# workflows-vasp-other-languages

This repository holds the *httk₂* VASP relaxation authored once per native
language SDK of *httk-workflow*: Ada, C, C++, Fortran, Java, Perl, and Rust.
Each directory is a self-contained workflow package, referenced directly by a
git commit, like those of [workflows-vasp](https://github.com/httk/workflows-vasp).
Every runner is a bridge client of the SDK in the installed *httk-workflow*,
so it publishes the same protocol bytes as a Python or Bash runner.

| Directory | Short name | Language |
| --- | --- | --- |
| `vasp-relax-ada` | `vasp.relax-ada` | Ada 2012 |
| `vasp-relax-c` | `vasp.relax-c` | C99 |
| `vasp-relax-cpp` | `vasp.relax-cpp` | C++17 |
| `vasp-relax-fortran` | `vasp.relax-fortran` | Fortran 2008 |
| `vasp-relax-java` | `vasp.relax-java` | Java 17 |
| `vasp-relax-perl` | `vasp.relax-perl` | Perl 5 |
| `vasp-relax-rust` | `vasp.relax-rust` | Rust 2021 |

All seven share one shape: `prepare` stages the payload POSCAR (and INCAR, if
present) into the workdir, `run` runs the configured VASP command under
supervision and classifies the result, and `publish` copies the finished
calculation into the job's transactional data when the job has it. `prepare`
uses each SDK's `stage_input` verb, so no runner copies files itself. They
declare the same workflow semantics as `vasp.relax` (the same
`declaration.json`, input `structure` and outputs `relaxed_structure` and
`total_energy`), and each `collect.py` calls
`httk.workflow.codes.vasp.collect.collect_vasp_relax`. They are deliberately
minimal starting points: the remedy ladder, derived INCAR tags, and POTCAR
assembly of `vasp.relax` are not reimplemented here.

## Job parameters

Every member is optional: `poscar` (default `files/POSCAR`), `incar` (default
`files/INCAR`), `timeout` (default `86400`), `data_prefix` (default `vasp`),
and `vasp_command`, the VASP command as one whitespace-split argv string. The
`vasp.command` workspace setting overrides `vasp_command`:

```console
httk workspace settings set --key vasp.command --value 'mpirun vasp_std' WORKSPACE
```

The packages default to `data.mode` `none`: the persistent workdir is the
result. Pass `--data-mode transactional` to `httk job new` to also publish the
files into `data/`.

## Building

Every package except Perl declares `[workflow.build]`. Build and register it
once per workspace and platform class (`uname -sm`; Java bytecode has no
platform tag) before a manager runs its jobs:

```console
httk workflow build --workspace WORKSPACE ./vasp-relax-c
```

The build command is `make`, which compiles against the installed SDK in
`$HTTK_WORKFLOW_LANGUAGES_DIR/<language>`, a variable `httk workflow build`
exports. The Rust package copies the SDK crate to `target/sdk` first, since
Cargo cannot expand an environment variable in a path dependency. Package
publication transfers sources only, and no package carries a `run` bridge
script: each manifest's `[workflow.runner] command` names what the manager
runs. The compiled packages declare `command = ["{artifacts}/relax"]` (Java:
`["java", "-cp", "{artifacts}/classes", "Relax"]`), which the manager expands
to the registered build. The Perl package needs no build: its command is
`["perl", "{package}/relax.pl"]`, and the script loads the SDK from
`$HTTK_WORKFLOW_PERL_API`.

Toolchains needed on the building machine, besides `make`:

| Package | Toolchain |
| --- | --- |
| `vasp-relax-ada` | `gnatmake` (GNAT) and a C compiler (`cc`) |
| `vasp-relax-c` | a C compiler (`cc`) |
| `vasp-relax-cpp` | `g++` and a C compiler (`cc`) |
| `vasp-relax-fortran` | `gfortran` and a C compiler (`cc`) |
| `vasp-relax-java` | a JDK 17+ (`javac`); running needs `java` |
| `vasp-relax-perl` | `perl` (no build) |
| `vasp-relax-rust` | `cargo`; the build is `--offline` with no crates.io dependencies |

## Reference a workflow by commit

```console
httk job new --workflow 'git+https://github.com/httk/workflows-vasp-other-languages@<ref>#vasp-relax-c' --input structure=POSCAR
```

`<ref>` may be a commit, branch, or tag, or omitted for the default branch; it
is canonicalized to the full commit hash the repository is cloned at, and the
named subdirectory's `httk_workflow.toml` package is used. Once referenced,
its short name (e.g. `vasp.relax-c`) also resolves.

## Install as a plugin

```console
httk plugin install 'git+https://github.com/httk/workflows-vasp-other-languages'
```

installs all seven workflow packages listed in `httk_plugin.toml` at once.

## Testing

```console
make test
```

runs `pytest` on `tests/` against the installed *httk-workflow*. Each
language's end-to-end test builds its package with `httk workflow build`,
runs one relaxation job through a real task manager with the mock VASP in
`tests/mock_vasp.py`, and collects it; it is skipped when that language's
toolchain is missing. `HTTK_TEST_PROFILE=extended` also runs each package with
transactional data.
