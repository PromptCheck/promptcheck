from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union, Literal
from pydantic import BaseModel, Field
import re

from promptcheck.core.schemas import TestCase, MetricThreshold # RENAMED
from promptcheck.core.providers import LLMResponse # RENAMED

from rouge_score import rouge_scorer, scoring
import nltk
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction

class MetricResult(BaseModel):
    metric_name: str
    score: Union[float, bool, str, Dict[str, Any]] # Flexible score type
    passed: Optional[bool] = None # True if thresholds are met, False otherwise, None if not applicable
    details: Optional[Dict[str, Any]] = None # For any additional metric-specific details
    error: Optional[str] = None # If an error occurred during metric calculation

# Helper function for comparisons
def _cmp(actual: float, operator: Literal[">=", "<="], threshold: float) -> bool:
    return actual >= threshold if operator == ">=" else actual <= threshold

class Metric(ABC):
    """Abstract Base Class for all metrics."""

    metric_name: str # Must be defined by subclasses, e.g., "exact_match", "rouge_l"

    def __init__(self, metric_config: Dict[str, Any]): # metric_config from TestCase.metric_configs
        """
        Initializes the metric with its specific configuration from the test case.
        """
        self.config = metric_config
        raw_threshold_config = metric_config.get('threshold') or metric_config.get('thresholds')
        if isinstance(raw_threshold_config, dict):
            try:
                self.threshold_config: Optional[MetricThreshold] = MetricThreshold(**raw_threshold_config)
            except Exception as e: # Catch Pydantic validation error or other issues
                # print(f"Warning: Could not parse threshold config for {self.metric_name}: {e}") # Optional logging
                self.threshold_config = None # Set to None if parsing fails
        else:
            self.threshold_config: Optional[MetricThreshold] = None

    @abstractmethod
    def calculate(self, test_case: TestCase, llm_response: LLMResponse) -> MetricResult:
        """
        Calculates the metric score based on the LLM's response and the test case's expected output.

        Args:
            test_case: The TestCase object containing expected outputs and metric configs.
            llm_response: The LLMResponse object from the provider.
        
        Returns:
            A MetricResult object.
        """
        pass

    def evaluate_thresholds(self, score: Any) -> Optional[bool]:
        """
        Evaluates if the given score meets the configured thresholds using the generic _cmp helper.
        Returns True if passed, False if failed, None if no threshold/value is applicable or score is not numeric.
        """
        if self.threshold_config is None or self.threshold_config.value is None or not isinstance(score, (int, float)):
            return None # No threshold value to evaluate against or score is not numeric
        
        # Ensure score and threshold_config.value are float for comparison if they are numbers
        try:
            numeric_score = float(score)
            numeric_threshold_value = float(self.threshold_config.value)
        except (ValueError, TypeError):
            return None # Cannot convert score or threshold to float

        # Use the _cmp helper with the operator and value from MetricThreshold
        # The default operator in MetricThreshold is ">=". Specific metrics can override this.
        passed = _cmp(numeric_score, self.threshold_config.operator, numeric_threshold_value)
        return passed


# We will add concrete Metric implementations below this, like ExactMatchMetric.

class ExactMatchMetric(Metric):
    metric_name = "exact_match"

    def __init__(self, metric_config: Dict[str, Any]):
        super().__init__(metric_config)
        # No specific config needed for exact_match beyond what Metric base class handles

    def calculate(self, test_case: TestCase, llm_response: LLMResponse) -> MetricResult:
        if llm_response.error:
            return MetricResult(
                metric_name=self.metric_name, 
                score=False, # Or some other indicator of failure due to LLM error
                passed=False,
                error=f"Cannot calculate {self.metric_name} due to LLM call error: {llm_response.error}"
            )

        if llm_response.text_output is None:
            return MetricResult(
                metric_name=self.metric_name,
                score=False,
                passed=False,
                error=f"LLM response text is None, cannot perform exact match for test: {test_case.name}"
            )

        expected_str = test_case.expected_output.exact_match_string
        if expected_str is None:
            return MetricResult(
                metric_name=self.metric_name,
                score=False,
                passed=False,
                error=f"Expected output (exact_match_string) not defined for test: {test_case.name}"
            )
        
        actual_str = llm_response.text_output
        is_match = (actual_str == expected_str)

        # For exact_match, the score is boolean (match or not), and this directly implies pass/fail.
        return MetricResult(
            metric_name=self.metric_name,
            score=is_match,
            passed=is_match,
            details={
                "expected": expected_str,
                "actual": actual_str
            }
        )

# Example Usage (can be expanded later for testing):
if __name__ == '__main__':
    # Placeholder for more comprehensive Metric tests if needed
    print("Metric classes defined. Run specific tests for each metric implementation.")
    # Example Test for ExactMatchMetric
    sample_mc_config = {"metric": "exact_match"} # from TestCase.metric_configs list
    exact_match = ExactMatchMetric(metric_config=sample_mc_config["metric"])

    # Mock TestCase and LLMResponse for testing ExactMatchMetric
    mock_test_case_pass = TestCase(
        name="TestExactPass",
        input_data={"prompt": "Hi"}, # Corrected: uses input_data
        expected_output={"exact_match_string": "Hello there"}, # Corrected: uses expected_output
        metric_configs=[sample_mc_config] # Corrected: uses metric_configs
    )
    mock_llm_response_pass = LLMResponse(text_output="Hello there")
    result_pass = exact_match.calculate(mock_test_case_pass, mock_llm_response_pass)
    print(f"Exact Match (Pass) Result: {result_pass.model_dump_json(indent=2)}") # Corrected: .model_dump_json()
    assert result_pass.passed is True

    mock_test_case_fail = TestCase(
        name="TestExactFail",
        input_data={"prompt": "Hi"},
        expected_output={"exact_match_string": "General Kenobi"},
        metric_configs=[sample_mc_config]
    )
    mock_llm_response_fail = LLMResponse(text_output="Hello there")
    result_fail = exact_match.calculate(mock_test_case_fail, mock_llm_response_fail)
    print(f"Exact Match (Fail) Result: {result_fail.model_dump_json(indent=2)}")
    assert result_fail.passed is False

    mock_llm_response_error = LLMResponse(error="LLM timed out")
    result_llm_error = exact_match.calculate(mock_test_case_pass, mock_llm_response_error)
    print(f"Exact Match (LLM Error) Result: {result_llm_error.model_dump_json(indent=2)}")
    assert result_llm_error.passed is False and result_llm_error.error is not None

    mock_test_case_no_expected = TestCase(
        name="TestExactNoExpected",
        input_data={"prompt": "Hi"},
        expected_output={}, # No exact_match_string
        metric_configs=[sample_mc_config]
    )
    result_no_expected = exact_match.calculate(mock_test_case_no_expected, mock_llm_response_pass)
    print(f"Exact Match (No Expected String) Result: {result_no_expected.model_dump_json(indent=2)}")
    assert result_no_expected.passed is False and result_no_expected.error is not None

import re # For RegexMatchMetric

class RegexMatchMetric(Metric):
    metric_name = "regex"

    def __init__(self, metric_config: Dict[str, Any]):
        super().__init__(metric_config)
        # Configuration for regex flags (e.g., re.IGNORECASE) could be added here from metric_config if needed
        # For now, using default regex behavior.

    def calculate(self, test_case: TestCase, llm_response: LLMResponse) -> MetricResult:
        if llm_response.error:
            return MetricResult(
                metric_name=self.metric_name,
                score=False,
                passed=False,
                error=f"Cannot calculate {self.metric_name} due to LLM call error: {llm_response.error}"
            )
        
        if llm_response.text_output is None:
            return MetricResult(
                metric_name=self.metric_name,
                score=False,
                passed=False,
                error=f"LLM response text is None, cannot perform regex match for test: {test_case.name}"
            )

        regex_pattern = test_case.expected_output.regex_pattern
        if not regex_pattern:
            return MetricResult(
                metric_name=self.metric_name,
                score=False,
                passed=False,
                error=f"Expected output (regex_pattern) not defined for test: {test_case.name}"
            )
        
        actual_str = llm_response.text_output
        
        try:
            # For simplicity, we consider a match if re.search finds the pattern anywhere.
            # More complex logic (e.g., re.fullmatch, or specific group extraction) could be added.
            match = re.search(regex_pattern, actual_str)
            is_match = bool(match)
        except re.error as e:
            return MetricResult(
                metric_name=self.metric_name,
                score=False,
                passed=False,
                error=f"Invalid regex pattern '{regex_pattern}' for test '{test_case.name}': {e}"
            )

        return MetricResult(
            metric_name=self.metric_name,
            score=is_match,
            passed=is_match,
            details={
                "pattern": regex_pattern,
                "actual_text": actual_str,
                "match_found": is_match
            }
        )

# Further expand __main__ for RegexMatchMetric tests later if needed.

class RougeMetric(Metric):
    metric_name = "rouge_l_f1" 

    def __init__(self, metric_config: Dict[str, Any]):
        super().__init__(metric_config)
        self.rouge_type = metric_config.get("parameters", {}).get("rouge_type", "rougeL")
        self.score_key = metric_config.get("parameters", {}).get("score_key", "fmeasure")

    def calculate(self, test_case: TestCase, llm_response: LLMResponse) -> MetricResult:
        if llm_response.error:
            return MetricResult(
                metric_name=self.metric_name,
                score=0.0, # Default score on error
                passed=False,
                error=f"Cannot calculate ROUGE due to LLM call error: {llm_response.error}"
            )
        
        if llm_response.text_output is None:
            return MetricResult(
                metric_name=self.metric_name,
                score=0.0,
                passed=False,
                error=f"LLM response text is None, cannot calculate ROUGE for test: {test_case.name}"
            )

        if not test_case.expected_output.reference_texts:
            return MetricResult(
                metric_name=self.metric_name,
                score=0.0,
                passed=False,
                error=f"Reference texts not defined for ROUGE calculation in test: {test_case.name}"
            )

        actual_summary = llm_response.text_output
        # rouge_scorer expects a list of reference summaries, but our schema is already List[str]
        # For multiple references, rouge_score typically takes the best score against any reference.
        # The current rouge_scorer library calculates against each reference and we might need to aggregate.
        # However, the standard CLI behavior is to join references if multiple are given to `rouge` CLI.
        # Let's join them to simulate a single longer reference, or take the first for simplicity.
        # Taking the first reference for now for simplicity with rouge_scorer.
        # For multi-reference, one might iterate and average, or take max.
        if not test_case.expected_output.reference_texts:
            return MetricResult(metric_name=self.metric_name, score=0.0, passed=False, error="No reference texts provided for ROUGE.")
        
        reference_summary = "\n".join(test_case.expected_output.reference_texts) # Join multiple refs
        # Or, if an aggregation strategy (like max score over refs) is desired later:
        # scores_over_references = []
        # for ref_summ in test_case.expected_output.reference_texts:
        #     scorer = rouge_scorer.RougeScorer([self.rouge_type], use_stemmer=True)
        #     scores = scorer.score(ref_summ, actual_summary)
        #     scores_over_references.append(scores[self.rouge_type].fmeasure)
        # final_score = max(scores_over_references) if scores_over_references else 0.0

        scorer = rouge_scorer.RougeScorer([self.rouge_type], use_stemmer=True)
        # The scorer returns a dict, e.g., {'rougeL': Score(precision=..., recall=..., fmeasure=...)}
        scores = scorer.score(reference_summary, actual_summary)
        
        final_score_value = 0.0
        all_scores_details = {}
        if self.rouge_type in scores:
            score_obj = scores[self.rouge_type]
            if self.score_key == "fmeasure":
                final_score_value = score_obj.fmeasure
            elif self.score_key == "precision":
                final_score_value = score_obj.precision
            elif self.score_key == "recall":
                final_score_value = score_obj.recall
            all_scores_details = {
                "precision": score_obj.precision,
                "recall": score_obj.recall,
                "fmeasure": score_obj.fmeasure
            }

        # Call its own evaluate_thresholds, not super()
        passed_status = self.evaluate_thresholds(final_score_value) 

        return MetricResult(
            metric_name=self.metric_name, 
            score=final_score_value,
            passed=passed_status if passed_status is not None else (final_score_value >= 0.0), 
            details={"rouge_type": self.rouge_type, "score_key_used": self.score_key, "all_scores": all_scores_details}
        )
    
    def evaluate_thresholds(self, score: float) -> Optional[bool]:
        """Evaluate ROUGE score against f_score threshold if defined."""
        if not self.threshold_config or self.threshold_config.f_score is None:
            return None # No applicable threshold
        
        # For ROUGE f_score, higher is better (default operator is >=)
        return _cmp(score, self.threshold_config.operator, self.threshold_config.f_score)

class BleuMetric(Metric):
    metric_name = "bleu"

    def __init__(self, metric_config: Dict[str, Any]):
        super().__init__(metric_config)
        # N-gram for BLEU, e.g., 4 for BLEU-4. Default to 4.
        self.n_gram = metric_config.get("parameters", {}).get("n_gram", 4)
        if not isinstance(self.n_gram, int) or self.n_gram <= 0:
            # Fallback or raise error for invalid n_gram
            self.n_gram = 4 
        # Create weights for sentence_bleu based on n_gram
        # e.g., for n_gram=4, weights=(0.25, 0.25, 0.25, 0.25)
        #        for n_gram=1, weights=(1.0, 0, 0, 0) - though NLTK handles this with (1,0,0,0) for BLEU-1
        self.weights = tuple(1/self.n_gram for _ in range(self.n_gram)) 
        # Smoothing function is often needed for short sentences or perfect matches
        self.smoothing_function = SmoothingFunction().method1 # A common choice

    def calculate(self, test_case: TestCase, llm_response: LLMResponse) -> MetricResult:
        if llm_response.error:
            return MetricResult(
                metric_name=self.metric_name,
                score=0.0,
                passed=False,
                error=f"Cannot calculate BLEU due to LLM call error: {llm_response.error}"
            )
        
        if llm_response.text_output is None:
            return MetricResult(
                metric_name=self.metric_name,
                score=0.0,
                passed=False,
                error=f"LLM response text is None, cannot calculate BLEU for test: {test_case.name}"
            )

        if not test_case.expected_output.reference_texts:
            return MetricResult(
                metric_name=self.metric_name,
                score=0.0,
                passed=False,
                error=f"Reference texts not defined for BLEU calculation in test: {test_case.name}"
            )

        hypothesis = llm_response.text_output.split() # NLTK expects tokenized input
        references = [ref.split() for ref in test_case.expected_output.reference_texts]

        if not hypothesis: # Handle empty hypothesis
            return MetricResult(metric_name=self.metric_name, score=0.0, passed=False, details={"n_gram": self.n_gram, "warning": "Hypothesis is empty after tokenization."})
        if not any(references): # Handle all empty references
            return MetricResult(metric_name=self.metric_name, score=0.0, passed=False, details={"n_gram": self.n_gram, "warning": "All reference texts are empty after tokenization."})

        try:
            # NLTK's sentence_bleu calculates score based on a list of reference token lists
            # and a hypothesis token list.
            bleu_score = sentence_bleu(
                references,
                hypothesis,
                weights=self.weights[:len(hypothesis)] if len(hypothesis) < self.n_gram else self.weights, # Adjust weights if hypothesis is too short
                smoothing_function=self.smoothing_function
            )
        except Exception as e:
            return MetricResult(
                metric_name=self.metric_name,
                score=0.0,
                passed=False,
                error=f"Error during NLTK BLEU calculation for test '{test_case.name}': {e}",
                details={"n_gram": self.n_gram}
            )

        passed_status = super().evaluate_thresholds(bleu_score) # Use base class method

        return MetricResult(
            metric_name=f"bleu-{self.n_gram}", # e.g., bleu-4
            score=bleu_score,
            passed=passed_status if passed_status is not None else (bleu_score > 0.0), # Default pass if score > 0 and no threshold
            details={"n_gram": self.n_gram}
        )
    
    # evaluate_thresholds method removed

class TokenCountMetric(Metric):
    metric_name = "token_count"

    def __init__(self, metric_config: Dict[str, Any]):
        super().__init__(metric_config)
        # Example: parameters: { count_types: ["prompt", "completion", "total"] }
        # Default to all if not specified
        self.count_types = metric_config.get("parameters", {}).get("count_types", ["prompt", "completion", "total"])
        if not isinstance(self.count_types, list) or not self.count_types:
            self.count_types = ["prompt", "completion", "total"]

    def calculate(self, test_case: TestCase, llm_response: LLMResponse) -> MetricResult:
        if llm_response.error:
            return MetricResult(
                metric_name=self.metric_name,
                score={}, # Score will be a dict of counts
                passed=False, # Fails if LLM call failed
                error=f"Cannot report token counts due to LLM call error: {llm_response.error}"
            )
        
        counts = {}
        if "prompt" in self.count_types and llm_response.prompt_tokens is not None:
            counts["prompt_tokens"] = llm_response.prompt_tokens
        if "completion" in self.count_types and llm_response.completion_tokens is not None:
            counts["completion_tokens"] = llm_response.completion_tokens
        if "total" in self.count_types and llm_response.total_tokens is not None:
            counts["total_tokens"] = llm_response.total_tokens
        
        if not counts: # If no relevant token info was found or requested
            return MetricResult(
                metric_name=self.metric_name,
                score={},
                passed=True, # Or False/None depending on strictness for missing token info
                details={"message": "No token counts available or requested for this response."}
            )

        # Threshold evaluation for token counts can be complex (e.g., max completion tokens)
        # The `evaluate_thresholds` method in the base class or an override here would handle it.
        # For now, we just report the counts. Thresholds can be for individual counts.
        passed_status = self.evaluate_thresholds(counts) 

        return MetricResult(
            metric_name=self.metric_name,
            score=counts, # The "score" is the dictionary of counts
            passed=passed_status if passed_status is not None else True, # Default to True if no thresholds set
            details={"count_types_reported": list(counts.keys())}
        )

    def evaluate_thresholds(self, scores: Dict[str, int]) -> Optional[bool]:
        """Override to handle specific threshold logic for token counts."""
        if not self.threshold_config: 
            return None
        
        overall_pass = True 
        threshold_conditions_met = False

        # self.threshold_config is a MetricThreshold object
        if self.threshold_config.completion_max is not None and "completion_tokens" in scores:
            threshold_conditions_met = True
            # For completion_max, actual <= threshold is a pass.
            # We use _cmp with the appropriate operator.
            # If user specifies an operator for completion_max in YAML, it would be used.
            # If not, MetricThreshold.operator defaults to ">=", which is wrong for a "max" type.
            # So, we assume completion_max implies "<=".
            # This highlights a limitation of a single operator in MetricThreshold if not overridden.
            # Let's assume completion_max implicitly means operator should be "<=" here.
            # A more robust MetricThreshold could have per-field operators or type of threshold.
            if not _cmp(float(scores["completion_tokens"]), "<=", float(self.threshold_config.completion_max)):
                overall_pass = False
        
        # Add checks for other potential thresholds like `prompt_max`, `total_max` etc.
        # if self.threshold_config.prompt_max ...

        return overall_pass if threshold_conditions_met else None

# Further expand __main__ for TokenCountMetric tests later if needed.

class LatencyMetric(Metric):
    metric_name = "latency"

    def __init__(self, metric_config: Dict[str, Any]):
        super().__init__(metric_config)
        # For latency, lower is better. If an operator isn't explicitly set
        # in the threshold_config, default it to "<=".
        if self.threshold_config and self.threshold_config.value is not None and self.threshold_config.operator == ">=":
             # Only override if a value is present and operator is the default (which means user didn't specify one)
             # Or, more simply, if a specific operator for latency wasn't given, assume '<='
             # Let's assume if user provides an operator, they know what they are doing.
             # If threshold_config was created from YAML that *didn't* specify an operator,
             # MetricThreshold defaults to ">=". For latency, we want "<=" by default.
            if not metric_config.get('threshold', {}).get('operator') and not metric_config.get('thresholds', {}).get('operator'):
                 self.threshold_config.operator = "<="

    def calculate(self, test_case: TestCase, llm_response: LLMResponse) -> MetricResult:
        if llm_response.error:
            return MetricResult(
                metric_name=self.metric_name,
                score=-1, 
                passed=False,
                error=f"Cannot report latency due to LLM call error: {llm_response.error}"
            )
        
        if llm_response.latency_ms is None:
            return MetricResult(
                metric_name=self.metric_name,
                score=-1,
                passed=False, 
                error=f"LLM response missing latency_ms for test: {test_case.name}",
                details={"message": "Latency information not available from provider."}
            )
        
        latency = llm_response.latency_ms
        passed_status = super().evaluate_thresholds(latency) # Use base class method

        return MetricResult(
            metric_name=self.metric_name,
            score=latency, 
            passed=passed_status if passed_status is not None else True, 
            details={"unit": "ms"}
        )

    # evaluate_thresholds method removed, now uses base class implementation.

# Further expand __main__ for LatencyMetric tests later if needed.

# Placeholder for pricing information. In a real system, this might come from a config file or API.
# Prices are per 1K tokens (input, output)
# Example: { "provider": { "model_name": {"input_cost_per_1k_tokens": X, "output_cost_per_1k_tokens": Y }}} 
DEFAULT_PLACEHOLDER_PRICING = {
    "openai": {
        "gpt-3.5-turbo": {"input_cost_per_1k_tokens": 0.0005, "output_cost_per_1k_tokens": 0.0015},
        "gpt-4o": {"input_cost_per_1k_tokens": 0.005, "output_cost_per_1k_tokens": 0.015},
        "default": {"input_cost_per_1k_tokens": 0.001, "output_cost_per_1k_tokens": 0.002} # Fallback for other openai models
    },
    "groq": {
        "llama3-8b-8192": {"input_cost_per_1k_tokens": 0.00005, "output_cost_per_1k_tokens": 0.00005}, # Example, check actual Groq pricing
        "mixtral-8x7b-32768": {"input_cost_per_1k_tokens": 0.0001, "output_cost_per_1k_tokens": 0.0001},
        "default": {"input_cost_per_1k_tokens": 0.0001, "output_cost_per_1k_tokens": 0.0001}
    },
    "openrouter": {
        # OpenRouter costs vary by the actual underlying model. 
        # The X-OpenRouter-Cost header is the best source if available. 
        # This placeholder is less accurate for OpenRouter.
        "default": {"input_cost_per_1k_tokens": 0.001, "output_cost_per_1k_tokens": 0.002} 
    },
    "default": { # Fallback for unknown providers
        "default": {"input_cost_per_1k_tokens": 0.001, "output_cost_per_1k_tokens": 0.002}
    }
}

class CostMetric(Metric):
    metric_name = "cost"

    def __init__(self, metric_config: Dict[str, Any]):
        super().__init__(metric_config)
        self.pricing_data = metric_config.get("parameters", {}).get("pricing_data", DEFAULT_PLACEHOLDER_PRICING)
        # For cost, lower is better. Default operator to "<=" if not specified by user.
        if self.threshold_config and self.threshold_config.value is not None:
            if not metric_config.get('threshold', {}).get('operator') and not metric_config.get('thresholds', {}).get('operator'):
                 self.threshold_config.operator = "<="

    def calculate(self, test_case: TestCase, llm_response: LLMResponse) -> MetricResult:
        if llm_response.error:
            return MetricResult(
                metric_name=self.metric_name,
                score=-1.0, 
                passed=False,
                error=f"Cannot calculate cost due to LLM call error: {llm_response.error}"
            )

        calculated_cost: Optional[float] = None
        source = "unknown"

        if llm_response.cost is not None:
            calculated_cost = llm_response.cost
            source = "provider_reported"
        else:
            prompt_tokens = llm_response.prompt_tokens
            completion_tokens = llm_response.completion_tokens
            model_name = llm_response.model_name_used
            
            provider_name = "unknown_provider"
            # Try to infer provider from model_name_used if it contains a '/' (e.g., "openrouter/...")
            # or from the test_case.case_model_config.provider
            if model_name and "/" in model_name:
                provider_name = model_name.split('/')[0].lower() # Use the part before '/' as provider
            elif test_case.case_model_config and test_case.case_model_config.provider != "default":
                provider_name = test_case.case_model_config.provider.lower()
            # else: it remains "unknown_provider" and will use the default pricing section


            if prompt_tokens is None or completion_tokens is None or model_name is None:
                return MetricResult(
                    metric_name=self.metric_name, score=-1.0, passed=False, 
                    details={"message": "Token counts or model name missing for cost calculation."},
                    error="Incomplete token/model info from provider."
                )

            provider_pricing = self.pricing_data.get(provider_name, self.pricing_data.get("default", {}))
            
            # If specific model_name (without provider prefix) is in pricing, use it. Otherwise, use provider's default.
            model_key_in_provider_pricing = model_name.split('/')[-1] if '/' in model_name else model_name
            model_pricing = provider_pricing.get(model_key_in_provider_pricing, provider_pricing.get("default", {}))


            if not model_pricing or "input_cost_per_1k_tokens" not in model_pricing or "output_cost_per_1k_tokens" not in model_pricing:
                return MetricResult(
                    metric_name=self.metric_name, score=-1.0, passed=False,
                    details={"provider": provider_name, "model": model_name, "message": "Pricing info not found."},
                    error="Pricing not available."
                )
            
            input_cost = (prompt_tokens / 1000) * model_pricing["input_cost_per_1k_tokens"]
            output_cost = (completion_tokens / 1000) * model_pricing["output_cost_per_1k_tokens"]
            calculated_cost = input_cost + output_cost
            source = "calculated"

        passed_status = super().evaluate_thresholds(calculated_cost) if calculated_cost is not None else False

        return MetricResult(
            metric_name=self.metric_name,
            score=calculated_cost if calculated_cost is not None else -1.0,
            passed=passed_status if passed_status is not None else (True if calculated_cost is not None and self.threshold_config is None else False),
            details={"unit": "USD", "source": source}
        )

    # evaluate_thresholds method removed

# Metric Factory
_metric_classes = {
    ExactMatchMetric.metric_name: ExactMatchMetric,
    RegexMatchMetric.metric_name: RegexMatchMetric,
    RougeMetric.metric_name: RougeMetric, # Assumes rouge_l_f1 is the registered name
    "rougeL_f1": RougeMetric, # Explicit alias if needed, or ensure RougeMetric.metric_name is generic enough
    "rougeL": RougeMetric, # If RougeMetric handles this via parameters
    BleuMetric.metric_name: BleuMetric, # Assumes "bleu" is the base name, n-gram handled internally
    TokenCountMetric.metric_name: TokenCountMetric,
    LatencyMetric.metric_name: LatencyMetric,
    CostMetric.metric_name: CostMetric,
    # Add other metrics here
}

def get_metric_calculator(metric_name: str, metric_config_params: Dict[str, Any]) -> Optional[Metric]:
    """
    Factory function to get an instance of a metric calculator.

    Args:
        metric_name: The name of the metric (e.g., "exact_match", "rouge_l_f1").
        metric_config_params: The configuration dictionary for this specific metric instance 
                              (from the test_case.metric_configs list).

    Returns:
        An instance of the requested Metric calculator, or None if not found.
    """
    # Handle specific variations like rouge_l_f1, rouge_1, etc. mapping to RougeMetric
    # This is a simple way; a more complex mapping or parameter passing could exist.
    if metric_name.startswith("rouge") and "rouge_l_f1" in _metric_classes: # Default to our specific RougeMetric for now
        # The RougeMetric itself can parse out the specific type (e.g. rougeL, rouge1 from parameters)
        # For now, ensure the specific metric_name used in TestCase is in _metric_classes or handled.
        # If metric_name is "rouge_l", it should ideally be handled by RougeMetric based on its params.
        # Current RougeMetric is named "rouge_l_f1" so it expects that specific key.
        # Let's assume the metric_name in the test case YAML will match one of these keys.
        metric_class = _metric_classes.get(metric_name.lower())
        if metric_class:
            # Pass the full config dict for this metric, which includes its own name, params, and threshold
            return metric_class(metric_config=metric_config_params) 
    elif metric_name.startswith("bleu") and "bleu" in _metric_classes:
        metric_class = _metric_classes.get("bleu")
        if metric_class:
            return metric_class(metric_config=metric_config_params)

    metric_class = _metric_classes.get(metric_name.lower())
    if metric_class:
        return metric_class(metric_config=metric_config_params)
    return None 