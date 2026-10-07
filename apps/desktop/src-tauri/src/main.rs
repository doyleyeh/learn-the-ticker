#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
use std::{io::{BufRead, BufReader, Write}, process::{Child, Command, Stdio}, sync::{mpsc, Mutex}, time::{Duration, Instant}};
use rand::{distributions::Alphanumeric, Rng};
use serde::Serialize;
use tauri::{Manager, menu::{Menu, MenuItem}, tray::TrayIconBuilder};

#[derive(Clone, Serialize)]
struct Bootstrap { endpoint: String, token: String }
struct Service { child: Child, bootstrap: Bootstrap }
#[derive(Default)]
struct State(Mutex<Option<Service>>);

fn stop_owned(child: &mut Child) {
    drop(child.stdin.take());
    let deadline = Instant::now() + Duration::from_secs(30);
    while Instant::now() < deadline {
        if matches!(child.try_wait(), Ok(Some(_))) { return; }
        std::thread::sleep(Duration::from_millis(100));
    }
    // Only this owned sidecar is terminated. A surviving private database is
    // authenticated and recovered by the next supervisor; no process search/kill.
    let _ = child.kill();
    let _ = child.wait();
}

struct PendingChild(Option<Child>);
impl Drop for PendingChild {
    fn drop(&mut self) { if let Some(child) = self.0.as_mut() { stop_owned(child); } }
}

fn start(app: &tauri::AppHandle) -> Result<Service, String> {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).ancestors().nth(3).ok_or("Missing workspace")?;
    let data = app.path().app_local_data_dir().map_err(|_| "Cannot locate private storage")?;
    std::fs::create_dir_all(&data).map_err(|_| "Cannot create private storage")?;
    let token: String = rand::thread_rng().sample_iter(&Alphanumeric).take(64).map(char::from).collect();
    let mut command;
    let pg_bin;
    if cfg!(debug_assertions) {
        let python = root.join(if cfg!(windows) { ".venv/Scripts/python.exe" } else { ".venv/bin/python" });
        command = Command::new(python);
        command.args(["-m", "backend.app.entrypoint"]).current_dir(root);
        pg_bin = std::env::var("LTT_PG_BIN").map_err(|_| "Set LTT_PG_BIN to a PostgreSQL bin directory for the developer preview")?;
    } else {
        let resource = app.path().resource_dir().map_err(|_| "Cannot locate runtime resources")?;
        let binary = std::env::current_exe().map_err(|_| "Cannot locate application")?.parent().ok_or("Missing application directory")?.join(if cfg!(windows) { "ltt-service.exe" } else { "ltt-service" });
        command = Command::new(binary);
        // initdb invokes its sibling postgres through legacy Windows path APIs.
        // Simplify verbatim paths only when their ordinary spelling is equivalent.
        let postgres_path = resource.join("resources/postgres/bin");
        pg_bin = dunce::simplified(&postgres_path).to_str().ok_or("Unsupported PostgreSQL resource path")?.to_owned();
    }
    #[cfg(windows)] { use std::os::windows::process::CommandExt; command.creation_flags(0x08000000); }
    let mut pending = PendingChild(Some(command.stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::null()).spawn().map_err(|_| "Cannot start packaged application service")?));
    let child = pending.0.as_mut().ok_or("Missing owned process")?;
    let config = serde_json::json!({"token": token, "data_dir": data, "pg_bin": pg_bin});
    writeln!(child.stdin.as_mut().ok_or("Missing bootstrap input")?, "{}", config).map_err(|_| "Bootstrap write failed")?;
    let stdout = child.stdout.take().ok_or("Missing bootstrap output")?;
    let (sender, receiver) = mpsc::channel();
    std::thread::spawn(move || {
        let mut line = String::new();
        let result = BufReader::new(stdout).read_line(&mut line).map(|_| line);
        let _ = sender.send(result);
    });
    let line = receiver.recv_timeout(Duration::from_secs(120)).map_err(|_| "Local startup timed out")?.map_err(|_| "Bootstrap read failed")?;
    let reply: serde_json::Value = serde_json::from_str(&line).map_err(|_| "Invalid startup response")?;
    let endpoint = reply.get("endpoint").and_then(|v| v.as_str()).ok_or("Local service could not start; verify database runtime, credentials and library lock")?.to_owned();
    let port = endpoint.strip_prefix("http://127.0.0.1:").and_then(|value| value.parse::<u16>().ok()).ok_or("Invalid local endpoint")?;
    if port == 0 { return Err("Invalid local endpoint".into()); }
    let agent = ureq::AgentBuilder::new().timeout(Duration::from_secs(2)).redirects(0).try_proxy_from_env(false).build();
    let mut ready = false;
    for _ in 0..15 {
        if let Ok(response) = agent.get(&format!("{}/api/health", endpoint)).set("Authorization", &format!("Bearer {}", token)).call() {
            if response.status() == 200 { ready = true; break; }
        }
        std::thread::sleep(Duration::from_millis(200));
    }
    if !ready { return Err("Authenticated readiness failed".into()); }
    Ok(Service { child: pending.0.take().ok_or("Missing owned process")?, bootstrap: Bootstrap { endpoint, token } })
}

#[tauri::command]
async fn bootstrap(app: tauri::AppHandle) -> Result<Bootstrap, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let state = app.state::<State>();
        let mut service = state.0.lock().map_err(|_| "Supervisor lock failed")?;
        if service.is_none() { *service = Some(start(&app)?); }
        Ok(service.as_ref().unwrap().bootstrap.clone())
    }).await.map_err(|_| "Supervisor failed")?
}

fn shutdown(app: &tauri::AppHandle) {
    if let Ok(mut guard) = app.state::<State>().0.lock() {
        if let Some(mut service) = guard.take() {
            stop_owned(&mut service.child);
        }
    }
}

fn main() {
    tauri::Builder::default().manage(State::default())
        .plugin(tauri_plugin_single_instance::init(|app, _, _| { if let Some(window) = app.get_webview_window("main") { let _ = window.show(); let _ = window.set_focus(); } }))
        .invoke_handler(tauri::generate_handler![bootstrap])
        .setup(|app| {
            let show = MenuItem::with_id(app, "show", "Open Learn the Ticker", true, None::<&str>)?;
            let quit = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show, &quit])?;
            TrayIconBuilder::new().icon(tauri::image::Image::new_owned([24, 86, 64, 255].repeat(32 * 32), 32, 32)).menu(&menu).tooltip("Learn the Ticker").on_menu_event(|app, event| match event.id.as_ref() {
                "show" => { if let Some(window) = app.get_webview_window("main") { let _ = window.show(); let _ = window.set_focus(); } },
                "quit" => { shutdown(app); app.exit(0); }, _ => {}
            }).build(app)?;
            Ok(())
        })
        .on_window_event(|window, event| { if let tauri::WindowEvent::CloseRequested { api, .. } = event { api.prevent_close(); let _ = window.hide(); } })
        .build(tauri::generate_context!()).expect("Desktop startup failed")
        .run(|app, event| { if let tauri::RunEvent::Exit = event { shutdown(app); } });
}
