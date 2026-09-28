//! One VASP relaxation, authored in safe Rust: the same three-step shape as
//! `vasp-relax-c/relax.c`, built on the installed native Rust SDK.
//!
//!   prepare  stage the payload POSCAR (and INCAR if present) into the workdir
//!   run      run the configured VASP command and classify what it did
//!   publish  copy the finished calculation into the job's transactional data
//!
//! Every `Attempt` method reaches the same `$HTTK_WORKFLOW_PYTHON -m
//! httk.workflow._shell_bridge` implementation the Python, Bash, C, and Fortran
//! SDKs do, so this runner is mock-vasp compatible and publishes the same bytes.
//! Build it with the Makefile beside this file (it stages the installed SDK crate
//! under `target/sdk` first, so a bare `cargo build` is not enough):
//!
//!     make
//!
//! See tests/mock_vasp.py for a stand-in VASP, and README.md for the whole flow.

use std::env;
use std::path::Path;

use httk_workflow::{Attempt, Runner, StepError};

/// The files a finished relaxation publishes, if the run produced them.
const COLLECT: &[&str] = &[
    "INCAR",
    "KPOINTS",
    "OUTCAR",
    "CONTCAR",
    "OSZICAR",
    "vasprun.xml",
    "vasp-run-report.json",
];

fn step_prepare(attempt: &Attempt) -> Result<(), StepError> {
    if !attempt.stage_input("poscar", "POSCAR", Some("files/POSCAR"))? {
        let _ = attempt.fail("vasp.input_missing", "the starting structure is not in this payload", false);
        return Ok(());
    }
    // An INCAR is optional; the mock VASP reads only the POSCAR.
    let _ = attempt.stage_input("incar", "INCAR", Some("files/INCAR"));
    let _ = attempt.runlog_note("prepared a relaxation");
    let _ = attempt.advance("run", &[]);
    Ok(())
}

fn step_run(attempt: &Attempt) -> Result<(), StepError> {
    let from_parameter = attempt.parameter("vasp_command", Some(""))?.unwrap_or_default();
    let command = attempt.setting("vasp.command", Some(&from_parameter))?.unwrap_or_default();
    if command.trim().is_empty() {
        let _ = attempt.fail(
            "vasp.command_missing",
            "no VASP command is configured: set it with \
             httk workspace settings set --key vasp.command --value '...' WORKSPACE, or set \
             HTTK_VASP_COMMAND, or give the job a vasp_command parameter",
            false,
        );
        return Ok(());
    }

    let timeout = attempt
        .parameter("timeout", Some("86400"))?
        .unwrap_or_else(|| "86400".to_string());

    // The resolved command is one argv string; split it on whitespace, the way
    // the Bash runner leaves it unquoted for the shell to word-split.
    let tokens: Vec<&str> = command.split_whitespace().collect();
    let mut args: Vec<&str> = vec!["--timeout", &timeout, "--report", "vasp-run-report.json", "--"];
    args.extend_from_slice(&tokens);

    let status = attempt.run(&args)?;
    if status == 0 {
        let _ = attempt.state_set("classification", "completed");
        let _ = attempt.runlog_note("VASP completed");
        let _ = attempt.advance("publish", &[]);
    } else {
        let _ = attempt.fail("vasp.failed", &format!("VASP did not complete (status {status})"), false);
    }
    Ok(())
}

fn step_publish(attempt: &Attempt) -> Result<(), StepError> {
    let prefix = attempt
        .parameter("data_prefix", Some("vasp"))?
        .unwrap_or_else(|| "vasp".to_string());
    let data_dir = env::var("HTTK_WORKFLOW_DATA_DIR").unwrap_or_default();
    let to_data = !data_dir.is_empty();
    for &name in COLLECT {
        if !Path::new(name).is_file() {
            continue;
        }
        if to_data {
            let _ = attempt.put(name, &format!("{prefix}/{name}"));
        }
    }
    let _ = attempt.runlog_note(if to_data {
        "published to transactional data"
    } else {
        "kept the result in the workdir"
    });
    let _ = attempt.succeed();
    Ok(())
}

fn main() {
    Runner::new("vasp.relax-rust", &["prepare", "run", "publish"])
        .step("prepare", step_prepare)
        .step("run", step_run)
        .step("publish", step_publish)
        .main();
}
