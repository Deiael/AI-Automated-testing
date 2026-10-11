from ai_test_contracts import EngineRequest, FlowType
from app.graphs.execute_graph import run_execute_stream
from app.graphs.testcase_graph import run_testcase_stream
from app.graphs.testpoint_graph import run_testpoint_stream


def stream_for(req: EngineRequest):
    if req.flow == FlowType.TEST_POINT:
        return run_testpoint_stream(req)
    if req.flow == FlowType.TEST_CASE:
        return run_testcase_stream(req)
    if req.flow == FlowType.TEST_EXECUTE:
        return run_execute_stream(req)
    raise ValueError(f"unsupported flow: {req.flow}")
