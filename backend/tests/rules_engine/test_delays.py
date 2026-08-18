from supervisor_ai.rules_engine.delays import evaluate_pause_delay


def test_interval_twenty_minute_boundaries() -> None:
    assert not evaluate_pause_delay(
        pause_type="Intervalo 20min", duration_seconds=20 * 60 + 59
    ).is_delay
    assert evaluate_pause_delay(
        pause_type="Intervalo 20min", duration_seconds=21 * 60
    ).is_delay


def test_bathroom_boundaries() -> None:
    assert not evaluate_pause_delay(
        pause_type="Banheiro", duration_seconds=5 * 60
    ).is_delay
    assert evaluate_pause_delay(
        pause_type="Banheiro", duration_seconds=5 * 60 + 1
    ).is_delay


def test_non_normative_pauses_are_ignored() -> None:
    for pause_type in (
        "Reunião",
        "COL. SUPERVISOR",
        "Intervalo 1 Hora",
        "Intervalo 2 Horas",
    ):
        assert not evaluate_pause_delay(
            pause_type=pause_type, duration_seconds=24 * 60 * 60
        ).is_delay
