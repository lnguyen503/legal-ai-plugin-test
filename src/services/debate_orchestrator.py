"""
Doer/Reviewer Debate Orchestrator for Legal Analysis

Implements a structured Doer/Reviewer debate where:
- DOER: executes the legal analysis workflow
- REVIEWER: critically challenges the analysis
- Multiple rounds with configurable exchanges per round
- Consensus synthesis at the end
"""
import json
import re
from typing import Generator, Dict, Any, Optional
from .llm_service import LLMService


DOER_SYSTEM_TEMPLATE = """You are the DOER — a meticulous legal analyst executing this analysis workflow.

WORKFLOW TO FOLLOW:
{plugin_content}

INSTRUCTIONS:
- Execute the workflow above against the provided document
- Be thorough, specific, and cite relevant sections of the document by clause number or section name
- Provide actionable findings with specific references
- Do not be defensive — if the Reviewer raises valid points, acknowledge and incorporate them
- Your goal is the most accurate analysis possible, not winning an argument
- Format your output exactly as specified in the workflow"""

REVIEWER_SYSTEM_TEMPLATE = """You are the REVIEWER — a senior legal analyst who critically reviews analysis work.

WORKFLOW STANDARD:
{plugin_content}

INSTRUCTIONS:
- Review the Doer's analysis against the workflow standard above
- Check thoroughly for: missed clauses, misinterpretations, incorrect risk classifications, gaps in coverage, logical errors, and unsupported conclusions
- FIRST steel-man the Doer's analysis — explicitly state what they got right before critiquing
- Be specific — cite exactly what was missed or misread, with document references where possible
- Suggest concrete, actionable improvements — not vague criticism
- Your goal is to strengthen the final output quality, not to attack the Doer
- If the analysis is largely correct, say so clearly and note only genuine gaps"""

SYNTHESIS_SYSTEM = """You are a senior legal analyst synthesizing a Doer/Reviewer debate into a final unified analysis.
Your job is to produce the highest-quality legal analysis by combining the best insights from both sides."""

SYNTHESIS_TEMPLATE = """You are synthesizing the final consensus from a Doer/Reviewer legal analysis debate.

ORIGINAL WORKFLOW:
{plugin_content}

DOER'S FINAL POSITION:
{doer_final}

REVIEWER'S FINAL POSITION:
{reviewer_final}

INSTRUCTIONS:
- Produce a unified analysis that incorporates the best from both positions
- Where they agree, state the agreed finding clearly
- Where they disagree, present both views and note which has stronger document support
- Flag any items where human legal judgment is essential
- Format the output according to the workflow's specified output format
- Be comprehensive — this is the final deliverable"""

CONSENSUS_CHECK_PROMPT = """Given these two positions from a legal analysis debate, have they reached substantial consensus (75%+ agreement on key findings)?

DOER'S LATEST POSITION (excerpt):
{doer_excerpt}

REVIEWER'S LATEST POSITION (excerpt):
{reviewer_excerpt}

Respond with JSON only, no other text:
{{"reached": true_or_false, "reasoning": "one sentence explanation"}}"""


class DoerReviewerOrchestrator:
    """
    Orchestrates a Doer/Reviewer debate for legal document analysis.
    Yields SSE-formatted event strings that the Flask endpoint can stream directly.
    """

    def __init__(self, llm_service: LLMService):
        self.llm = llm_service
        self.token_counts: Dict[str, int] = {"input_tokens": 0, "output_tokens": 0}

    def run_debate(
        self,
        document_text: str,
        plugin_content: str,
        context_notes: str,
        doer_model: str,
        reviewer_model: str,
        max_rounds: int = 3,
        exchanges_per_round: int = 3,
    ) -> Generator[str, None, None]:
        """
        Run the Doer/Reviewer debate and yield SSE event strings.

        Event types emitted:
          round_start     — beginning of a new debate round
          exchange_start  — about to call LLM for this exchange (show spinner)
          exchange        — full LLM response for a Doer/Reviewer exchange
          consensus_check — result of inter-round consensus evaluation
          synthesis_start — about to generate final synthesis
          synthesis       — the final combined analysis
          done            — debate complete, includes total token counts
          error           — something went wrong
        """
        self.token_counts = {"input_tokens": 0, "output_tokens": 0}

        doer_system = DOER_SYSTEM_TEMPLATE.format(plugin_content=plugin_content)
        reviewer_system = REVIEWER_SYSTEM_TEMPLATE.format(plugin_content=plugin_content)

        # Base document context prepended to every prompt
        context_block = f"\nADDITIONAL CONTEXT: {context_notes}\n" if context_notes.strip() else ""
        base_doc_prompt = f"""{context_block}
DOCUMENT TO ANALYZE:
{document_text}"""

        doer_last = ""
        reviewer_last = ""
        consensus_reached = False

        for round_num in range(1, max_rounds + 1):
            yield self._event({"type": "round_start", "round": round_num, "max_rounds": max_rounds})

            # ── Exchange 1: Doer produces/updates analysis ──────────────────
            if round_num == 1:
                doer_prompt = f"Please analyze the following legal document according to the workflow.\n{base_doc_prompt}"
                doer_label = "DOER: Initial Analysis"
            else:
                doer_prompt = (
                    f"Please analyze the following legal document according to the workflow.\n{base_doc_prompt}\n\n"
                    f"--- PREVIOUS DEBATE CONTEXT ---\n"
                    f"Your previous analysis:\n{doer_last}\n\n"
                    f"The Reviewer's critique:\n{reviewer_last}\n\n"
                    f"The Reviewer has challenged your analysis. Review their feedback carefully. "
                    f"Acknowledge valid points explicitly, defend positions where you have document evidence, "
                    f"and produce a revised, improved analysis that incorporates legitimate feedback."
                )
                doer_label = f"DOER: Revised Analysis (Round {round_num})"

            yield self._event({"type": "exchange_start", "role": "DOER", "round": round_num, "exchange": 1, "label": doer_label})
            doer_response, doer_usage = self.llm.call_model(
                model=doer_model, prompt=doer_prompt, system_prompt=doer_system, temperature=0.7, max_tokens=8192
            )
            doer_last = doer_response
            self._add_tokens(doer_usage)
            yield self._event({"type": "exchange", "role": "DOER", "round": round_num, "exchange": 1, "label": doer_label, "text": doer_response})

            # ── Exchange 2: Reviewer challenges ─────────────────────────────
            if round_num == 1:
                reviewer_prompt = (
                    f"Please analyze the following legal document according to the workflow.\n{base_doc_prompt}\n\n"
                    f"--- DOER'S ANALYSIS TO REVIEW ---\n{doer_response}\n\n"
                    f"Critically review the Doer's analysis. First acknowledge what they got right, "
                    f"then identify missed clauses, misinterpretations, incorrect classifications, or gaps."
                )
                reviewer_label = "REVIEWER: Initial Challenge"
            else:
                reviewer_prompt = (
                    f"Please analyze the following legal document according to the workflow.\n{base_doc_prompt}\n\n"
                    f"--- UPDATED DOER ANALYSIS ---\n{doer_response}\n\n"
                    f"--- YOUR PREVIOUS CRITIQUE ---\n{reviewer_last}\n\n"
                    f"Evaluate whether the Doer adequately addressed your previous concerns. "
                    f"Acknowledge what was resolved. Raise any remaining substantive issues clearly."
                )
                reviewer_label = f"REVIEWER: Follow-up (Round {round_num})"

            yield self._event({"type": "exchange_start", "role": "REVIEWER", "round": round_num, "exchange": 2, "label": reviewer_label})
            reviewer_response, reviewer_usage = self.llm.call_model(
                model=reviewer_model, prompt=reviewer_prompt, system_prompt=reviewer_system, temperature=0.7, max_tokens=8192
            )
            reviewer_last = reviewer_response
            self._add_tokens(reviewer_usage)
            yield self._event({"type": "exchange", "role": "REVIEWER", "round": round_num, "exchange": 2, "label": reviewer_label, "text": reviewer_response})

            # ── Exchange 3: Doer responds to Reviewer (if exchanges >= 3) ───
            if exchanges_per_round >= 3:
                doer_response_prompt = (
                    f"Please analyze the following legal document according to the workflow.\n{base_doc_prompt}\n\n"
                    f"--- YOUR ANALYSIS ---\n{doer_response}\n\n"
                    f"--- REVIEWER'S CRITIQUE ---\n{reviewer_response}\n\n"
                    f"Respond to the Reviewer's specific concerns. Acknowledge valid points with document evidence, "
                    f"defend positions where warranted, and state your refined position clearly."
                )
                doer_resp_label = f"DOER: Response to Critique (Round {round_num})"
                yield self._event({"type": "exchange_start", "role": "DOER", "round": round_num, "exchange": 3, "label": doer_resp_label})
                doer_resp, dr_usage = self.llm.call_model(
                    model=doer_model, prompt=doer_response_prompt, system_prompt=doer_system, temperature=0.6, max_tokens=8192
                )
                doer_last = doer_resp
                self._add_tokens(dr_usage)
                yield self._event({"type": "exchange", "role": "DOER", "round": round_num, "exchange": 3, "label": doer_resp_label, "text": doer_resp})

                # ── Exchange 4: Reviewer follow-up (if exchanges >= 4) ──────
                if exchanges_per_round >= 4:
                    reviewer_fu_prompt = (
                        f"Please analyze the following legal document according to the workflow.\n{base_doc_prompt}\n\n"
                        f"--- DOER'S RESPONSE ---\n{doer_resp}\n\n"
                        f"--- YOUR PREVIOUS CRITIQUE ---\n{reviewer_response}\n\n"
                        f"Has the Doer adequately addressed your concerns? Acknowledge resolved issues clearly. "
                        f"Raise only genuine remaining substantive issues. Work toward consensus."
                    )
                    reviewer_fu_label = f"REVIEWER: Evaluation (Round {round_num})"
                    yield self._event({"type": "exchange_start", "role": "REVIEWER", "round": round_num, "exchange": 4, "label": reviewer_fu_label})
                    reviewer_fu, rfu_usage = self.llm.call_model(
                        model=reviewer_model, prompt=reviewer_fu_prompt, system_prompt=reviewer_system, temperature=0.6, max_tokens=8192
                    )
                    reviewer_last = reviewer_fu
                    self._add_tokens(rfu_usage)
                    yield self._event({"type": "exchange", "role": "REVIEWER", "round": round_num, "exchange": 4, "label": reviewer_fu_label, "text": reviewer_fu})

                    # ── Exchange 5: Consensus attempt (if exchanges >= 5) ───
                    if exchanges_per_round >= 5:
                        doer_consensus_prompt = (
                            f"Please analyze the following legal document according to the workflow.\n{base_doc_prompt}\n\n"
                            f"The debate has progressed through several exchanges. "
                            f"Synthesize your final position, acknowledging the strongest points from both sides. "
                            f"Propose a final unified analysis that addresses all major concerns raised."
                        )
                        doer_cons_label = f"DOER: Consensus Position (Round {round_num})"
                        yield self._event({"type": "exchange_start", "role": "DOER", "round": round_num, "exchange": 5, "label": doer_cons_label})
                        doer_cons, dc_usage = self.llm.call_model(
                            model=doer_model, prompt=doer_consensus_prompt, system_prompt=doer_system, temperature=0.5, max_tokens=8192
                        )
                        doer_last = doer_cons
                        self._add_tokens(dc_usage)
                        yield self._event({"type": "exchange", "role": "DOER", "round": round_num, "exchange": 5, "label": doer_cons_label, "text": doer_cons})

            # ── Consensus check between rounds ───────────────────────────────
            if round_num < max_rounds:
                consensus_result = self._check_consensus(doer_last, reviewer_last, doer_model)
                yield self._event({
                    "type": "consensus_check",
                    "round": round_num,
                    "reached": consensus_result["reached"],
                    "reasoning": consensus_result["reasoning"],
                })
                if consensus_result["reached"]:
                    consensus_reached = True
                    break
            else:
                yield self._event({
                    "type": "consensus_check",
                    "round": round_num,
                    "reached": False,
                    "reasoning": "Maximum rounds reached — proceeding to forced synthesis.",
                })

        # ── Final Synthesis ───────────────────────────────────────────────────
        yield self._event({"type": "synthesis_start"})

        synthesis_prompt = SYNTHESIS_TEMPLATE.format(
            plugin_content=plugin_content,
            doer_final=doer_last,
            reviewer_final=reviewer_last,
        )
        synthesis_text, synth_usage = self.llm.call_model(
            model=doer_model,
            prompt=synthesis_prompt,
            system_prompt=SYNTHESIS_SYSTEM,
            temperature=0.5,
            max_tokens=8192,
        )
        self._add_tokens(synth_usage)

        yield self._event({"type": "synthesis", "text": synthesis_text})
        yield self._event({
            "type": "done",
            "token_counts": self.token_counts,
            "final_analysis": synthesis_text,
        })

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _check_consensus(self, doer_text: str, reviewer_text: str, model: str) -> Dict[str, Any]:
        """Quick consensus check using a short excerpt from each position."""
        prompt = CONSENSUS_CHECK_PROMPT.format(
            doer_excerpt=doer_text[:1500],
            reviewer_excerpt=reviewer_text[:1500],
        )
        try:
            response, _ = self.llm.call_model(
                model=model,
                prompt=prompt,
                system_prompt="You are a neutral consensus evaluator. Respond only with valid JSON.",
                temperature=0.2,
                max_tokens=150,
            )
            json_match = re.search(r"\{.*?\}", response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    "reached": bool(result.get("reached", False)),
                    "reasoning": str(result.get("reasoning", "Consensus evaluated.")),
                }
        except Exception:
            pass
        return {"reached": False, "reasoning": "Unable to evaluate consensus — continuing debate."}

    def _add_tokens(self, usage: Dict[str, int]) -> None:
        self.token_counts["input_tokens"] += usage.get("input_tokens", 0)
        self.token_counts["output_tokens"] += usage.get("output_tokens", 0)

    def _event(self, data: Dict[str, Any]) -> str:
        """Format a dict as an SSE data line."""
        return f"data: {json.dumps(data)}\n\n"
