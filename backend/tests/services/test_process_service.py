from app.engine.analyzer.process_analyzer import ProcessAnalyzer

def test_process_analyzer():
    result = ProcessAnalyzer().analyze("Weekly PDF email process")
    assert result["automationScore"] > 0
