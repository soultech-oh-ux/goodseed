//! Embedded, update-resistant assistant runtime. Uses the bundled Python and installed Codex CLI.
use std::io::Write;

pub fn run(args: &[String]) -> Result<(), String> {
    let exe = std::env::current_exe().map_err(|e| e.to_string())?;
    let base = exe.parent().ok_or("실행 파일 폴더가 없습니다")?;
    let bundled = base.join("runtime/python/python3.exe");
    let python = if bundled.is_file() {
        bundled.into_os_string()
    } else {
        #[cfg(windows)]
        let name = "python";
        #[cfg(not(windows))]
        let name = "python3";
        name.into()
    };
    let nonce = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH)
        .map_err(|e| e.to_string())?.as_nanos();
    let script = std::env::temp_dir().join(format!("gsd-assistant-{}-{nonce}.py", std::process::id()));
    let mut file = std::fs::OpenOptions::new().write(true).create_new(true).open(&script)
        .map_err(|e| format!("AI 런타임 준비 실패: {e}"))?;
    let prepared = file.write_all(include_bytes!("../scripts/gsd-assistant.py"));
    drop(file);
    let result = prepared.map_err(|e| e.to_string()).and_then(|_| {
        let mut command = std::process::Command::new(python);
        // Stdlib-only runtime: avoid user site startup hooks and force Korean UTF-8 output.
        command.args(["-I", "-S", "-X", "utf8"]).arg(&script).args(args);
        if let Some(path) = crate::runtime_prefixed_path(base, &std::env::var("PATH").unwrap_or_default()) {
            command.env("PATH", path);
        }
        let status = command.status().map_err(|e| format!("AI 실행 실패(Python 3 필요): {e}"))?;
        if status.success() { Ok(()) } else { Err("AI 작업을 완료하지 못했습니다. 위 메시지를 확인하세요.".into()) }
    });
    let _ = std::fs::remove_file(&script);
    result
}
