# CLO command-line options (CLO_Standalone_OnlineAuth_x64.exe 2026.1.336)

*Status: static analysis only (disassembly of the option registration code plus string scan). Option semantics beyond the registered names/help text are inference.*
*Date: 2026-10-29*
*Lane J. Scripts used: `scripts/disasm_fn.py`, `scripts/xref_rip.py`, `scripts/iat_name.py`. Related: `findings/11_impl_util_import_export.md` (IsHeadless), `findings/17_log_message_catalog.md`.*

All addresses are RVAs (image base 0x140000000). CLO is a Qt 6 application, so the standard Qt options of `QApplication`/`QGuiApplication` (for example `-platform`, `-style`, `-stylesheet`, `-qwindowgeometry`, `-display`) are also consumed before CLO sees the arguments; those are not CLO strings and are not catalogued here.

## 1. The `IsHeadless()` parser (RVA 0x6268a40)

Disassembly summary (83 instructions):

```
QCommandLineParser p;
p.setSingleDashWordOptionMode(ParseAsLongOptions);     // IAT ?setSingleDashWordOptionMode (edx=1): "-headless x" == "--headless x"
p.addHelpOption();  p.addVersionOption();              // -h/--help, -v/--version (Qt built-ins)
QCommandLineOption o(/*name*/"headless", /*desc*/tr("Run python file at <file>."),
                     /*valueName*/"headless", /*default*/"");   // QCommandLineOption(QString,QString,QString,QString)
p.addOption(o);
p.parse(QCoreApplication::arguments());               // parse(), NOT process(): never prints help / never exits
return p.isSet(o);
```

* Only **one** CLO option is registered here: `headless` (takes a value: the python file to run). Nothing else in this parser (not `-headlessconfig`, `-remote`, ...) counts for the gate.
* Because `parse()` is used, unknown options do not terminate CLO. Whether `isSet` still reports a correctly spelled `-headless` when other unknown options are present depends on Qt's behaviour on unknown options (it records an error but I did not verify that parsing continues) - treat as unverified.
* The function is called on every use (no caching seen at this level), builds a fresh parser each time.

### Effect on the plugin API (headless gating)

| API | Gate | Behaviour when CLO is **not** started with `-headless` | Source |
|---|---|---|---|
| `ImportAPI::ImportMeasurement` (`.csv`) | `IsHeadless()` (0x6268a40) | returns `false` (no message) | `findings/11` |
| `ImportAPI::ImportFile` | none seen | returns `true` when no document is open (not headless related) | `findings/11` |
| `ImportAPI::ImportAvatar`, `ImportAvatarMeasurement` | no headless check | work in GUI mode (crash risk is the ABI issue, not this gate) | `findings/11` |
| `UtilityAPI::DisplayMessageBox` and GuiAPI `Ask*` | no headless check | open a modal dialog even in headless mode (can block) | `findings/11` |
| login | in headless mode CLO uses the API-key flow (section 2), not the web login | | strings `[Python] RequestHeadlessLogin ...` |

Consequence for Mirra: the REST plugin runs inside a normal GUI CLO session, so `ImportMeasurement` is unavailable; the working route is `ImportAvatar` / `.avs`/`ImportFile`-style imports (as already noted in the repo memory). Starting CLO with `-headless <script.py>` would enable `ImportMeasurement` but also switches CLO into headless init (RVA 0x62b2c80: `[Python] Running on Headless Mode`, loads `Resources_Common.rcc`, `Resources_Dark/Light.rcc`, a `plugins` folder, installs the `[Headless][Level]` message handler at 0x62b3ee0 and runs the python file, then `[Python] Exit Headless mode.`). Whether a REST plugin loaded from `pluginSettings.json` is started in that mode was **not** analysed; do not assume it is.

## 2. Full registered option set (the headless family)

Two near-identical registration routines register the same 12 options: region A 0x345ea90-0x345f668 (`ends 14345F668`) and region B 0x345f6a0-0x3460201 (B additionally ends with a `GoZ` string, so it is the variant used for the second pass / different caller). Both begin with the same `QCommandLineParser` setup as above. Strings are at 0x8414f08-0x84150b8. Names and help text are exact (the single-letter strings `r`, `a`, `s`, `m`, `d` sit next to the corresponding option in the registration code; whether each is the primary name or an alias of the long name was not resolved); "Takes value" is inferred from whether a value-name string (the third `QCommandLineOption` argument) is built.

| Option (long name) | Short alias | Help string (exact) | Takes value? | Default | Notes |
|---|---|---|---|---|---|
| `headless` | - | `Run python file at <file>.` | yes (`<file>`) | "" | enables headless mode and `ImportMeasurement` |
| `headlessconfig` | - | `Register an access key and a secret key.` | not resolved | "" | registers headless API credentials with a CLO account; also checked as a raw `-headlessconfig` string (0x8a36f68) by the headless init at 0x62b3d2f |
| `remote` | `r` (string 0x82bc714) | `Executed in a remote environment.` | flag (inference) | | selects remote/server environment behaviour |
| `headlesslog` | - | `Writing a log file.` | flag (inference) | | turns on the headless log file; the `[Headless][%s] %s` handler is the formatter. Log file path not resolved. |
| `performlog` | - | `Perform log analysis` | flag (inference) | | log analysis mode |
| `accesskey` | `a` | `Headless API AccessKey.` | yes (`accesskey`) | "" | credential; **never put it in plugin logs** |
| `secretkey` | `s` | `Headless API SecretKey.` | yes (`secretkey`) | "" | credential; same |
| `id` | - | `User ID` | yes (`id`) | "" | CLO account id (used with `headlessconfig`) |
| `pw` | - | `User Password` | yes (`pw`) | "" | CLO account password; never log |
| `m` (value name `months`) | `m` | `Headless Key periods` | yes (`months`) | `1` (string 0x8265270) | validity period of the generated key |
| `description` | `d` | `Headless description` | yes (`description`) | "" | description of the key |
| `deleteKey` | - | `Delete headless API key` | not resolved | "" | revokes the key |

Related strings: `Writing a log file.` / `headlesslog` are the only log-file related options; `[Headless][%s] %s` (0x8a36fe0) with levels `[Debug]   `, `[Info]    `, `[Warning] `, `[Critical]`, `[Fatal]   ` and timestamp `yyyy-MM-dd hh:mm:ss` (0x8a36f78) is the message format.
Credential-related options (`accesskey`, `secretkey`, `id`, `pw`, `deleteKey`, `headlessconfig`) belong to the CLO account/licence subsystem; no attempt was made to evaluate them (project rule).

## 3. Other command-line / environment inputs seen in the exe

| Input | RVA | Kind | Meaning (inference) |
|---|---|---|---|
| `-headless` | 0x828cb38 | raw argv scan (string compare in 0x62b3ce0) | headless init looks for the literal single-dash words `-headless` and `-headlessconfig` in the raw arguments |
| `-headlessconfig` | 0x8a36f68 | raw argv scan | same |
| `CLO_HTTP_PROXY`, `CLO_HTTPS_PROXY` | 0x8a3700e, 0x8a37020 | environment variables | message `Please remove CLO_HTTP_PROXY or CLO_HTTPS_PROXY in your environment variable.` (0x8a37000) - CLO objects to these; `Registered proxy server url : %s` (0x8a37050) |
| `--proxy-server=`, `--user-data-dir=`, `--disable-gpu`, `--disable-software-rasterizer`, `--no-sandbox` | 0x8a37170, 0x8a37190, 0x8a371c0, 0x8a371d0, 0x8a371f0 | Chromium flags assembled by CLO for QtWebEngine | not user options; `QTWEBENGINE_CHROMIUM_FLAGS`, `QT_WEBENGINE_DISABLE_GPU`, `QTWEBENGINE_DISABLE_SANDBOX`, `QSG_RHI_BACKEND` (value `opengl`) are set/read from the environment around them |
| `RENDERDOC_CAPTUREOPTS`, `RENDERDOC_CAPFILE`, `RENDERDOC_HOOKING`, `RENDERDOC_DEBUG_LOG_FILE`, `RENDERDOC_LOGFILE` | 0x8a370d0-0x8a37138 | environment variables | CLO clears/inspects RenderDoc hooking variables (anti-injection or compatibility) |
| `QT_SCALE_FACTOR` | 0x847deb0 | environment | HiDPI scale |
| `-normalize`, `-node`, `-no_lapack`, `-no_tbb` | 0x88d660e, 0x8910a1c, 0x8aaf370, 0x8aaf398 | strings inside bundled third-party/internal code (not CLO CLI) | ignore |

Not found: any registered `--version`/`--help` text of CLO's own (only the Qt built-ins), `-nosplash`, `-safe`, `-log`, `-debug`, `-open <file>` style options. Opening a `.zprj`/`.zpac` by passing it as a positional argument is handled elsewhere (file association) and was not analysed.

## 4. What this means for plugin development

* `-headless <file.py>` is the **only** switch that changes the plugin-visible API surface (`ImportMeasurement`). There is no CLI switch to turn on API logging; channel A (FUNCSIG events) is governed by the Logger's enabled flag (`findings/17`, O3).
* Headless mode is account-bound (API key login) and changes UI behaviour (no main window, `[Headless]` log lines); it is not a drop-in way to get `ImportMeasurement` under the REST plugin without a separate evaluation, and it involves licence/auth components that this project must not touch.
* Do not set `CLO_HTTP_PROXY` / `CLO_HTTPS_PROXY` in the environment that launches CLO.
* If CLO is started by a script, start it from a console and redirect stderr if you want to see Qt `[Python] ...` messages in GUI mode (inference, not tested).
