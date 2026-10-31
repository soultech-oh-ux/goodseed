//! Default output workspace. User-supplied terminal cwd remains authoritative.
use std::path::{Path, PathBuf};

fn resolve(override_dir: Option<&str>, desktop: Option<PathBuf>) -> Result<PathBuf, String> {
    let path = match override_dir.filter(|s| !s.trim().is_empty()) {
        Some(value) => PathBuf::from(value),
        None => desktop.ok_or("바탕화면 위치를 찾을 수 없습니다. GSD_OUTPUT_DIR에 절대경로를 지정하세요.")?.join("goodseed"),
    };
    if !path.is_absolute() {
        return Err("GSD_OUTPUT_DIR은 절대경로여야 합니다.".into());
    }
    Ok(path)
}

fn ensure(path: &Path) -> Result<(), String> {
    std::fs::create_dir_all(path).map_err(|e| format!("결과물 폴더를 준비하지 못했습니다 ({}): {e}", path.display()))
}

/// Respect Windows Desktop redirection (including OneDrive), rather than guessing USERPROFILE/Desktop.
pub fn default_dir() -> Result<PathBuf, String> {
    let configured = std::env::var("GSD_OUTPUT_DIR").ok();
    let path = resolve(configured.as_deref(), dirs::desktop_dir())?;
    ensure(&path)?;
    Ok(path)
}

pub fn skill_output_dir() -> Result<PathBuf, String> {
    let path = default_dir()?.join("_round").join("skill-out");
    ensure(&path)?;
    Ok(path)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn desktop_redirection_and_unicode_paths_are_preserved() {
        let desktop = std::env::temp_dir().join("OneDrive").join("한글 Desktop");
        assert_eq!(resolve(None, Some(desktop.clone())).unwrap(), desktop.join("goodseed"));
        let chosen = std::env::temp_dir().join("선택한 결과 폴더");
        assert_eq!(resolve(Some(chosen.to_str().unwrap()), None).unwrap(), chosen);
    }
    #[test]
    fn invalid_override_and_missing_desktop_fail_explicitly() {
        assert!(resolve(Some("relative/output"), Some(std::env::temp_dir())).is_err());
        assert!(resolve(None, None).is_err());
        assert_eq!(resolve(Some("  "), Some(std::env::temp_dir())).unwrap(), std::env::temp_dir().join("goodseed"));
    }
    #[test]
    fn nested_output_is_created_and_file_collision_is_an_error() {
        let root = std::env::temp_dir().join(format!("gsd-workspace-test-{}", std::process::id()));
        let nested=root.join("결과").join("하위 폴더");
        ensure(&nested).unwrap();
        assert!(nested.is_dir());
        let file=root.join("file");
        std::fs::write(&file,b"keep").unwrap();
        assert!(ensure(&file).is_err());
        assert_eq!(std::fs::read(&file).unwrap(),b"keep");
        let target=std::fs::canonicalize(&root).unwrap();
        let allowed=std::fs::canonicalize(std::env::temp_dir()).unwrap();
        assert!(target.starts_with(&allowed));
        assert!(target.file_name().unwrap().to_string_lossy().starts_with("gsd-workspace-test-"));
        std::fs::remove_dir_all(target).unwrap();
    }
}
