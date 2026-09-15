from classifier import parse_response


def test_valid_four_line_output():
    text = """PROVISION: Prohibits Chinese state-linked entities from participating in the U.S. bulk-power system.
TOPIC: Energy, Grid & Electrical Infrastructure
TOPIC_CONFIDENCE: 95
TOPIC_RUNNER_UP: Sanctions & Export Controls"""
    result = parse_response(text)
    assert result.topic == "Energy, Grid & Electrical Infrastructure"
    assert result.confidence == 95


def test_rule_suffix_runner_up_is_accepted():
    text = """PROVISION: Prohibits federal procurement of solar panels manufactured in China.
TOPIC: Energy, Grid & Electrical Infrastructure
TOPIC_CONFIDENCE: 85
TOPIC_RUNNER_UP: Federal Procurement & Buy American (rule 2b)"""
    result = parse_response(text)
    assert result.confidence == 85
    assert "(rule 2b)" in result.runner_up
