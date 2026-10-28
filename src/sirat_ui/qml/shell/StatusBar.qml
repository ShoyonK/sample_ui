import QtQuick 2.15

StatusBarForm {
    messageLabel.text: app.state.statusMessage
    backendLabel.text: app.state.backendText
    releaseLabel.text: app.state.releaseText
    activityLabel.text: app.state.activityText
}
