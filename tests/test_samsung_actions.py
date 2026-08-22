from nphonekit_samsung_actions import SamsungFrpActions, samsung_2022_commands


def test_samsung_2022_commands_preserve_sequence_shape():
    commands = samsung_2022_commands()

    assert len(commands) == 97
    assert commands[:6] == [
        "AT+SWATD=0", "AT+ACTIVATE=0,0,0", "AT+DEVCONINFO",
        "AT+KSTRINGB=0,3", "AT+DUMPCTRL=1,0", "AT+DEBUGLVC=0,5",
    ]
    assert commands[6:13] == commands[13:20]
    assert commands[-1] == "AT+DEBUGLVC=0,5"


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
