# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Test file for action detector utils."""


import os
import pytest
import pandas as pd
import json
import hashlib
from pyspark.sql import Row
from datetime import datetime
from action_analyzer.contracts.actions.action import ActionType, Action
from action_analyzer.contracts.action_sample import ActionSample, IndexActionSample
from action_analyzer.contracts.utils.detector_utils import (
    extract_retrieval_info,
    generate_index_action_samples,
    get_index_id_from_index_content,
    deduplicate_actions
)
from action_analyzer.action_detector_component.run import (
    get_unique_indexes,
    parse_hashed_index_id,
    get_violated_metrics
)
from shared_utilities.span_tree_utils import (
    SpanTree,
    SpanTreeNode,
)
from shared_utilities.constants import (
    PROMPT_COLUMN,
    MODIFIED_PROMPT_COLUMN,
    COMPLETION_COLUMN,
    INDEX_SCORE_LLM_COLUMN,
    ROOT_SPAN_COLUMN,
    RETRIEVAL_QUERY_TYPE_COLUMN,
    RETRIEVAL_TOP_K_COLUMN,
    PROMPT_FLOW_INPUT_COLUMN,
    INDEX_SCORE_COLUMN,
    RETRIEVAL_DOC_COLUMN,
    INDEX_ID_COLUMN,
    INDEX_CONTENT_COLUMN,
    SPAN_ID_COLUMN
)


@pytest.fixture
def df_for_action_sample():
    """Return a df for generating action sample."""
    df = pd.DataFrame(columns=[
        PROMPT_COLUMN,
        MODIFIED_PROMPT_COLUMN,
        COMPLETION_COLUMN,
        INDEX_SCORE_LLM_COLUMN,
        ROOT_SPAN_COLUMN,
        RETRIEVAL_QUERY_TYPE_COLUMN,
        RETRIEVAL_TOP_K_COLUMN,
        PROMPT_FLOW_INPUT_COLUMN
    ])

    for i in range(10):
        df = df.append({
            PROMPT_COLUMN: 'Prompt',
            MODIFIED_PROMPT_COLUMN: 'Modified Prompt',
            COMPLETION_COLUMN: 'Completion',
            INDEX_SCORE_LLM_COLUMN: i,
            ROOT_SPAN_COLUMN: 'Root Span',
            RETRIEVAL_QUERY_TYPE_COLUMN: 'Query Type',
            RETRIEVAL_TOP_K_COLUMN: 5,
            PROMPT_FLOW_INPUT_COLUMN: 'Flow Input'
        }, ignore_index=True)
    return df


@pytest.fixture
def retrieval_root_span():
    """Return a root span for retrieval."""
    # The tree is structured like this:
    # 1
    # |-> 2 -> 3 (retrieval)
    # |-> 4 -> 5 (retreival)
    mlindex_content = '{"self": {"asset_id": "index_asset_id_1"}}'
    index_input = json.dumps({"mlindex_content": mlindex_content})
    attribute_str = json.dumps({"inputs": index_input})

    s1 = SpanTreeNode(
        Row(trace_id="01", span_id="1", parent_id=None, start_time=datetime(2024, 2, 12, 9, 0, 0),
            end_time=datetime(2024, 2, 12, 10, 5, 0)))
    s2 = SpanTreeNode(
        Row(trace_id="01", span_id="2", parent_id="1", start_time=datetime(2024, 2, 12, 9, 5, 0),
            end_time=datetime(2024, 2, 12, 9, 40, 0),
            attributes=attribute_str))
    s3 = SpanTreeNode(
        Row(trace_id="01", span_id="3", parent_id="2", start_time=datetime(2024, 2, 12, 9, 15, 0),
            end_time=datetime(2024, 2, 12, 9, 20, 0), span_type="Retrieval")
    )

    mlindex_content = '{"self": {"asset_id": "index_asset_id_2"}}'
    index_input = json.dumps({"mlindex_content": mlindex_content})
    attribute_str = json.dumps({"inputs": index_input})
    s4 = SpanTreeNode(
        Row(trace_id="01", span_id="4", parent_id="1", start_time=datetime(2024, 2, 12, 9, 25, 0),
            end_time=datetime(2024, 2, 12, 9, 30, 0),
            attributes=attribute_str))
    s5 = SpanTreeNode(
        Row(trace_id="01", span_id="5", parent_id="4", start_time=datetime(2024, 2, 12, 9, 45, 0),
            end_time=datetime(2024, 2, 12, 9, 50, 0), span_type="Retrieval")
    )

    spans = [s1, s2, s3, s4, s5]
    return SpanTree(spans).to_json_str()


@pytest.fixture
def root_span_without_retrieval():
    """Return a root span with no retrieval span."""
    # The tree only has one root node.
    s1 = SpanTreeNode(
        Row(trace_id="01", span_id="1", parent_id=None, start_time=datetime(2024, 2, 12, 9, 0, 0),
            end_time=datetime(2024, 2, 12, 10, 5, 0)))

    spans = [s1]
    return SpanTree(spans).to_json_str()


@pytest.fixture
def root_span():
    """Return a root span with all debugging info."""
    # The tree is structured like this:
    # 1
    # |-> 2 -> 3 (index1 retrieval)
    # |-> 4 -> 5 (index2 retrieval)
    s1 = SpanTreeNode(
        Row(trace_id="01", span_id="1", parent_id=None, start_time=datetime(2024, 2, 12, 9, 0, 0),
            end_time=datetime(2024, 2, 12, 10, 5, 0),
            attributes=json.dumps({"inputs": "prompt_flow_input"})))

    mlindex_content = '{"self": {"asset_id": "index_asset_id_1"}}'
    index_input = json.dumps({"mlindex_content": mlindex_content,
                              "query_type": "Hybrid (vector + keyword)",
                              "top_k": 3})
    lookup_attributes = json.dumps({"inputs": index_input})
    s2 = SpanTreeNode(
        Row(trace_id="01", span_id="2", parent_id="1", start_time=datetime(2024, 2, 12, 9, 5, 0),
            end_time=datetime(2024, 2, 12, 9, 40, 0),
            attributes=lookup_attributes))
    documents = []
    for i in range(3):
        documents.append({"document.content": f"doc_{i}", "document.score": "0.5"})

    retrieval_attributes = json.dumps({"retrieval.query": "query_3", "retrieval.documents": json.dumps(documents)})
    s3 = SpanTreeNode(
        Row(trace_id="01", span_id="3", parent_id="2", start_time=datetime(2024, 2, 12, 9, 15, 0),
            end_time=datetime(2024, 2, 12, 9, 20, 0), span_type="Retrieval", attributes=retrieval_attributes)
    )

    mlindex_content = '{"self": {"asset_id": "index_asset_id_2"}}'
    index_input = json.dumps({"mlindex_content": mlindex_content,
                              "query_type": "Hybrid (vector + keyword)",
                              "top_k": 3})
    lookup_attributes = json.dumps({"inputs": index_input})
    s4 = SpanTreeNode(
        Row(trace_id="01", span_id="4", parent_id="1", start_time=datetime(2024, 2, 12, 9, 5, 0),
            end_time=datetime(2024, 2, 12, 9, 40, 0),
            attributes=lookup_attributes))
    documents = []
    for i in range(3):
        documents.append({"document.content": f"doc_{i}", "document.score": "0.5"})

    retrieval_attributes = json.dumps({"retrieval.query": "query_5", "retrieval.documents": json.dumps(documents)})
    s5 = SpanTreeNode(
        Row(trace_id="01", span_id="5", parent_id="4", start_time=datetime(2024, 2, 12, 9, 15, 0),
            end_time=datetime(2024, 2, 12, 9, 20, 0), span_type="Retrieval", attributes=retrieval_attributes)
    )
    spans = [s1, s2, s3, s4, s5]
    return SpanTree(spans).to_json_str()


@pytest.fixture
def hashed_index_id_1():
    """Return a hashed index id 1."""
    index_content_1 = '{"self": {"asset_id": "index_asset_id_1"}}'
    return hashlib.sha256(index_content_1.encode('utf-8')).hexdigest()


@pytest.fixture
def hashed_index_id_2():
    """Return a hashed index id 2."""
    index_content_2 = '{"self": {"asset_id": "index_asset_id_2"}}'
    return hashlib.sha256(index_content_2.encode('utf-8')).hexdigest()


@pytest.mark.unit
class TestDetectorUtils:
    """Test class for action."""

    @pytest.mark.parametrize(
        "index_content, expected_index_id", [
            ('{"self": {"asset_id": "index_asset_id"}}', "index_asset_id"),
            ('{"index": {"index": "index_name"}}', "index_name"),
            ('{}', None),
            ('invalid_yaml', None)
        ])
    def test_get_index_id_from_index_content(self, index_content, expected_index_id):
        """Test get_index_id_from_index_content function."""
        result = get_index_id_from_index_content(index_content)
        assert result == expected_index_id

    def test_get_violated_metrics_success(self):
        """Test get violated metrics from gsq output."""
        # "AverageFluencyScore": {
        #     "value": "4.62",
        #     "threshold": "4.5",
        # }
        # "AverageCoherenceScore": {
        #     "value": "4.45",
        #     "threshold": "4.5",
        # }
        # "AverageRelevanceScore": {
        #     "value": "4.17",
        #     "threshold": "4.5",
        # }
        tests_path = os.path.abspath(f"{os.path.dirname(__file__)}/../../")
        input_url = f"{tests_path}/unit/action_analyzer/resources/"
        print(input_url)
        violated_metrics = get_violated_metrics(input_url, "gsq-signal")
        assert violated_metrics == ["Coherence", "Relevance"]

    def test_get_violated_metrics_fail(self):
        """Test get violated metrics from empty gsq output."""
        tests_path = os.path.abspath(f"{os.path.dirname(__file__)}/../../")
        input_url = f"{tests_path}/unit/action_analyzer/resources/"
        violated_metrics = get_violated_metrics(input_url, "empty")
        assert violated_metrics == []

    def test_generate_index_action_samples_negative(self, df_for_action_sample):
        """Test generate_index_action_samples function for negative samples."""
        action_samples = generate_index_action_samples(df_for_action_sample, True)
        assert len(action_samples) == 10
        assert isinstance(action_samples[0], IndexActionSample)
        # the score is not sorted for negative samples
        assert action_samples[0].lookup_score == 0
        assert action_samples[9].lookup_score == 9

    def test_generate_index_action_samples_positive(self, df_for_action_sample):
        """Test generate_index_action_samples function for positive samples."""
        action_samples = generate_index_action_samples(df_for_action_sample, False)
        assert len(action_samples) == 10
        assert isinstance(action_samples[0], IndexActionSample)
        # the score is sorted in descent order for positive samples
        assert action_samples[0].lookup_score == 9
        assert action_samples[9].lookup_score == 0

    def test_parse_hashed_index_id(self, retrieval_root_span, hashed_index_id_1, hashed_index_id_2):
        """Test parse_hashed_index_id function from the root span."""
        # The tree is structured like this:
        # 1
        # |-> 2 -> 3 (retrieval)
        # |-> 4 -> 5 (retreival)
        index_ids = parse_hashed_index_id(retrieval_root_span)
        assert len(index_ids) == 2
        assert hashed_index_id_1 in index_ids
        assert hashed_index_id_2 in index_ids

    def test_get_unique_indexes(self, retrieval_root_span, hashed_index_id_1, hashed_index_id_2):
        """Test get_unique_indexes function from the root span."""
        # The tree is structured like this:
        # 1
        # |-> 2 -> 3 (retrieval: index_asset_1)
        # |-> 4 -> 5 (retreival: index_asset_2)
        df = pd.DataFrame(columns=[ROOT_SPAN_COLUMN])
        for i in range(10):
            df = df.append({
                ROOT_SPAN_COLUMN: retrieval_root_span
            }, ignore_index=True)

        unique_indexes = get_unique_indexes(df)
        assert len(unique_indexes) == 2
        assert hashed_index_id_1 in unique_indexes
        assert hashed_index_id_2 in unique_indexes

    def test_get_unique_indexes_no_retreival_span(self, root_span_without_retrieval):
        """Test get_unique_indexes function from the root span with no retrieval span."""
        df = pd.DataFrame(columns=[ROOT_SPAN_COLUMN])
        for i in range(10):
            df = df.append({
                ROOT_SPAN_COLUMN: root_span_without_retrieval
            }, ignore_index=True)

        unique_indexes = get_unique_indexes(df)
        assert len(unique_indexes) == 0

    def test_extract_retrieval_info(self, root_span, hashed_index_id_1):
        """Test extract_retrieval_info function from the root span."""
        # The tree is structured like this:
        # 1
        # |-> 2 -> 3 (index1 retrieval)
        # |-> 4 -> 5 (index2 retrieval)
        retrieval_info_list = extract_retrieval_info(root_span, hashed_index_id_1)
        # only index 1 should be returned
        assert len(retrieval_info_list) == 1
        retrieval_info = json.loads(retrieval_info_list[0])
        print(retrieval_info)
        assert retrieval_info[SPAN_ID_COLUMN] == "3"
        assert retrieval_info[INDEX_CONTENT_COLUMN] == '{"self": {"asset_id": "index_asset_id_1"}}'
        assert retrieval_info[INDEX_ID_COLUMN] == "index_asset_id_1"
        assert retrieval_info[MODIFIED_PROMPT_COLUMN] == "query_3"
        assert retrieval_info[RETRIEVAL_DOC_COLUMN] == "doc_0#<Splitter>#doc_1#<Splitter>#doc_2"
        assert retrieval_info[INDEX_SCORE_COLUMN] == 0.5
        assert retrieval_info[RETRIEVAL_QUERY_TYPE_COLUMN] == "Hybrid (vector + keyword)"
        assert retrieval_info[RETRIEVAL_TOP_K_COLUMN] == 3
        assert retrieval_info[PROMPT_FLOW_INPUT_COLUMN] == "prompt_flow_input"

    def test_deduplicate_actions_should_dedup(self):
        """Test deduplicate_actions function. Actions have overlap > 50%."""
        # Total 6 actions. All have same negative queries. Confidence scores are 1, 0.9, 0.8, 0.95, 0.95, 0.95.
        positive_samples = []
        negative_samples = []
        for i in range(10):
            negative_samples.append(ActionSample(f"negative_query_{i}",
                                                 f"negative_answer_{i}",
                                                 f"negative_debugging_info_{i}",
                                                 f"negative_prompt_flow_input_{i}"))
        actions = []
        for i in range(3):
            actions.append(Action(ActionType.LOW_RETRIEVAL_SCORE_INDEX_ACTION,
                                  f"action_{i}",
                                  1 - i/10,
                                  "query intention",
                                  "deployment id",
                                  "run id",
                                  positive_samples,
                                  negative_samples))
        for i in range(3):
            actions.append(Action(ActionType.METRICS_VIOLATION_INDEX_ACTION,
                                  f"action_{i}",
                                  0.95,
                                  "query intention",
                                  "deployment id",
                                  "run id",
                                  positive_samples,
                                  negative_samples))

        deduplicated_list = deduplicate_actions(actions)
        assert len(deduplicated_list) == 1
        assert deduplicated_list[0].confidence_score == 1
        assert deduplicated_list[0].action_type == ActionType.LOW_RETRIEVAL_SCORE_INDEX_ACTION

    def test_deduplicate_actions_should_dedup_two_actions(self):
        """Test deduplicate_actions function. Actions have overlap > 50%."""
        # Total 6 actions. 3 of each have same queries. Confidence scores are 1, 0.9, 0.8, 0.95, 0.95, 0.95.
        positive_samples = []
        negative_samples_1 = []
        negative_samples_2 = []
        for i in range(10):
            negative_samples_1.append(ActionSample(f"negative_query_{i}",
                                                   f"negative_answer_{i}",
                                                   f"negative_debugging_info_{i}",
                                                   f"negative_prompt_flow_input_{i}"))
        for i in range(10):
            negative_samples_2.append(ActionSample(f"query_{i}",
                                                   f"answer_{i}",
                                                   f"debugging_info_{i}",
                                                   f"prompt_flow_input_{i}"))
        actions = []
        for i in range(3):
            actions.append(Action(ActionType.LOW_RETRIEVAL_SCORE_INDEX_ACTION,
                                  f"action_{i}",
                                  1 - i/10,
                                  "query intention",
                                  "deployment id",
                                  "run id",
                                  positive_samples,
                                  negative_samples_1))
        for i in range(3):
            actions.append(Action(ActionType.METRICS_VIOLATION_INDEX_ACTION,
                                  f"action_{i}",
                                  0.95,
                                  "query intention",
                                  "deployment id",
                                  "run id",
                                  positive_samples,
                                  negative_samples_2))

        deduplicated_list = deduplicate_actions(actions)
        assert len(deduplicated_list) == 2
        assert deduplicated_list[0].confidence_score == 1
        assert deduplicated_list[0].action_type == ActionType.LOW_RETRIEVAL_SCORE_INDEX_ACTION
        assert deduplicated_list[1].confidence_score == 0.95
        assert deduplicated_list[1].action_type == ActionType.METRICS_VIOLATION_INDEX_ACTION

    def test_deduplicate_actions_not_dedup(self):
        """Test deduplicate_actions function. Actions have overlap < 50%."""
        # Total 2 actions. The overlap is less than 50%.
        # action 1 has ['negative_query_1', 'negative_query_2', 'negative_query_3', 'negative_query_4']
        # action 2 has ['negative_query_4', 'negative_query_5', 'negative_query_6', 'negative_query_7', 'negative_query_8']  # noqa
        actions = []
        positive_samples = []
        negative_samples = []
        for i in range(1, 5):
            negative_samples.append(ActionSample(f"negative_query_{i}",
                                                 f"negative_answer_{i}",
                                                 f"negative_debugging_info_{i}",
                                                 f"negative_prompt_flow_input_{i}"))
        actions.append(Action(ActionType.METRICS_VIOLATION_INDEX_ACTION,
                              "action_1",
                              0.95,
                              "query intention",
                              "deployment id",
                              "run id",
                              positive_samples,
                              negative_samples))
        negative_samples = []
        for i in range(4, 9):
            negative_samples.append(ActionSample(f"negative_query_{i}",
                                                 f"negative_answer_{i}",
                                                 f"negative_debugging_info_{i}",
                                                 f"negative_prompt_flow_input_{i}"))
        actions.append(Action(ActionType.METRICS_VIOLATION_INDEX_ACTION,
                              "action_2",
                              0.95,
                              "query intention",
                              "deployment id",
                              "run id",
                              positive_samples,
                              negative_samples))
        deduplicated_list = deduplicate_actions(actions)
        assert deduplicated_list == actions
