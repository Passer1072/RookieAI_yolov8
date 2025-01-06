import threading
import Utils.revision as revision


def get_and_set(ui):
    ui.window.announcement.setMarkdown(
        revision.get_online_announcement())

    # 设置渠道类型
    ui.window.channelLabel.setText(revision.get_channel())

    # 设置当前版本号
    ui.window.versionLabel.setText(revision.get_local_version())

    # 设置当前版本日期
    ui.window.versionDateLabel.setText(
        revision.get_local_date())

    # 设置最新版版本号
    if revision.is_official_version():
        _version = revision.get_release_version_with_date()
    else:
        _version = revision.get_dev_version_with_date()
    _version = f"{_version[0]}({_version[1]})"
    ui.window.latestVersionLabel.setText(_version)


def get_announcement(ui):

    thread = threading.Thread(target=get_and_set, args=(ui,))
    thread.start()
    # 等待线程完成
    thread.join()
