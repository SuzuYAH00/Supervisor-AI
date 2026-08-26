from datetime import date, datetime

ATTENDANCE_CLOSED_ROW = {
    "attendance_id": 101,
    "protocol": "2699.10180",
    "customer_id": 7001,
    "opened_date": date(2026, 8, 20),
    "opened_time": "09:10:11",
    "closed_at": datetime(2026, 8, 20, 10, 30, 45, 123000),
    "opening_operator": "operator.open",
    "closing_operator": "operator.close",
    "process_id": 44,
    "subprocess_id": 71,
    "opening_classification_id": 81,
    "closing_classification_id": 91,
    "origin_id": 9,
    "status": "closed",
    "finalized": "S",
    "dialog_session_id": 501,
}

ATTENDANCE_OPEN_ROW = {
    **ATTENDANCE_CLOSED_ROW,
    "attendance_id": 102,
    "protocol": "2699.10200",
    "closed_at": None,
    "closing_operator": None,
    "closing_classification_id": None,
    "status": "open",
    "finalized": "N",
    "dialog_session_id": None,
}

DIALOG_EVALUATED_ROW = {
    "dialog_session_id": 501,
    "protocol": "2699.50010",
    "score": 5,
    "created_at": datetime(2026, 8, 20, 9, 9, 30),
    "human_service_started_at": datetime(2026, 8, 20, 9, 10),
    "closed_at": datetime(2026, 8, 20, 10, 30),
    "entered_queue_at": datetime(2026, 8, 20, 9, 9, 45),
    "sector_id": 10,
    "integration_code": "fixture-integration",
    "channel_type": "Whatsapp",
    "person_id": 7001,
}

DIALOG_UNANSWERED_ROW = {
    **DIALOG_EVALUATED_ROW,
    "dialog_session_id": 502,
    "protocol": "2699.50020",
    "score": None,
    "human_service_started_at": None,
    "closed_at": None,
}

DIALOG_OPERATOR_ROW = {
    "link_id": 9001,
    "dialog_session_id": 501,
    "user_id": 301,
    "joined_at": datetime(2026, 8, 20, 9, 10),
    "left_at": datetime(2026, 8, 20, 10, 30),
}

MK_USER_ROW = {
    "user_id": 301,
    "login": "fixture.operator",
    "name": "Operador Fictício",
}
