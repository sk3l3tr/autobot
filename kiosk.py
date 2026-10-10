import multiprocessing
multiprocessing.set_start_method('spawn', force=True)


def main():
    import webview, os, signal
    print("[KIOSK] Starting application ...")

    webview.settings['OPEN_DEVTOOLS_IN_DEBUG'] = False
    webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = True
    webview.settings['ALLOW_DOWNLOADS'] = True

    def on_window_closed():
        """Trigger application shutdown when window closes"""
        print("[KIOSK] Window closed, triggering shutdown...")
        # Send SIGTERM to parent process to trigger clean shutdown
        try:
            parent_pid = os.getppid()
            if os.name == "nt":
                os.kill(parent_pid, signal.CTRL_BREAK_EVENT)
            else:
                os.kill(parent_pid, signal.SIGTERM)
        except Exception as e:
            print(f"[KIOSK] Error signaling parent: {e}")
            os._exit(0)

    webview.create_window(
        title='Autobot',
        url='http://127.0.0.1:5555/index.html',
        background_color= '#000000',
        width=800,
        height=800,
        resizable=True,
        fullscreen=False,
        frameless=True,
        on_top=False,
    )
    
    try:
        webview.start(debug=True)
    finally:
        on_window_closed()

if __name__ == "__main__" and multiprocessing.current_process().name == "MainProcess":
    multiprocessing.freeze_support()
    main()