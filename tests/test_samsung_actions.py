from nphonekit_samsung_actions import SamsungFrpActions


def test_pre_aug2022_stops_when_user_declines():
    actions = SamsungFrpActions(
        strings={},
        load_methods=lambda path: [{
            "id": "sam_pre_2022",
            "title": "title",
            "desc": "desc",
            "pros": "pros",
            "cons": "cons",
            "minutes": 1,
        }],
        verinfo=lambda gui: "unused",
        at=None,
        adb=None,
        log_command_output=None,
        show_messagebox=None,
        success_checks=None,
        hardware_uuid=None,
        formrequest=None,
        confirm_method=lambda *args: False,
    )

    assert actions.pre_aug2022() is None


def test_pre_aug2022_reports_missing_device():
    reports = []
    actions = SamsungFrpActions(
        strings={"getVerInfo": "info", "deviceCheckPluggedIn2": "plug in"},
        load_methods=lambda path: [{
            "id": "sam_pre_2022",
            "title": "title",
            "desc": "desc",
            "pros": "pros",
            "cons": "cons",
            "minutes": 1,
        }],
        verinfo=lambda gui: "Fail",
        at=None,
        adb=None,
        log_command_output=None,
        show_messagebox=None,
        success_checks=lambda *args: reports.append(args),
        hardware_uuid=lambda: "uuid",
        formrequest=lambda: None,
        confirm_method=lambda *args: True,
    )

    actions.pre_aug2022()
    assert reports and reports[0][2:] == ("FRP_Unlock_Pre_2022", "Fail")
