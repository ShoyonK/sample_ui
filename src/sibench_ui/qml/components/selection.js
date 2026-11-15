.pragma library

// How a click on a list row selects (req 9, 18): Shift extends a range, Ctrl toggles the row, a plain click
// selects only that row. Matches RowSelection.select's modes in shared/selection.py.
function mode(modifiers) {
    if (modifiers & Qt.ShiftModifier)
        return "range"
    if (modifiers & Qt.ControlModifier)
        return "toggle"
    return "single"
}
