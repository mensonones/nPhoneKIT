"""Small UI helpers used by maintenance and diagnostics flows."""

def show_serial_permission_fix(command, tk_module=None):
    """Show the platform-specific serial permission command."""
    if tk_module is None:
        import tkinter as tk_module

    root = tk_module.Tk()
    root.title("Serial Permission Fix Required")
    root.geometry("500x250")
    label = tk_module.Label(
        root,
        text="To enable serial access, run this command in your terminal:",
        font=("Arial", 12),
    )
    label.pack(pady=10)
    text_box = tk_module.Text(root, height=2, font=("Courier", 12))
    text_box.pack(padx=20, pady=10, fill="both")
    text_box.insert("1.0", command)
    text_box.config(state="disabled")
    reboot_label = tk_module.Label(
        root,
        text="After running the command, reboot your system.",
        font=("Arial", 10),
    )
    reboot_label.pack(pady=10)
    ok_button = tk_module.Button(root, text="OK", command=root.destroy)
    ok_button.pack(pady=10)
    root.mainloop()


def get_output_text(window):
    """Read the output widget from the main window, if available."""
    if window is None:
        return ""
    return window.output.toPlainText()
