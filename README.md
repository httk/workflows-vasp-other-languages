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
calculation into the job's `data/` when the job sets `publish_data`. `prepare`
uses each SDK's `stage_input` verb, so no runner copies files itself. They
declare the same workflow semantics as `vasp.relax` (the same
`declaration.json`, input `structure` and outputs `relaxed_structure` and
`total_energy`), and each `collect.py` locates the CONTCAR and OUTCAR with
`record.result_file` and reads them with the `read_structure` and
`read_total_energy` helpers of `httk.codes.vasp.collect` from an installed *httk-workflow-vasp*
(`pip install httk-workflow-vasp`). They are
deliberately minimal starting points: the remedy ladder, derived INCAR tags,
and POTCAR assembly of `vasp.relax` are not reimplemented here.

## Job parameters

Every member is optional: `poscar` (default `files/POSCAR`), `incar` (default
`files/INCAR`), `timeout` (default `86400`), `publish_data` (default `false`),
`data_prefix` (default `vasp`), and `vasp_command`, the VASP command as one whitespace-split argv string. The
`vasp.command` workspace setting overrides `vasp_command`:

```console
httk workspace settings set --key vasp.command --value 'srun vasp_std' WORKSPACE
```

These native-language runners call the generic `run` verb, which is not
code-aware: it runs `vasp.command` exactly as given and never prepends the
attempt's launch prefix (`HTTK_WORKFLOW_LAUNCH`). On a cluster without
confinement the command must therefore include the site launcher, as above, and
the runners do not run in parallel inside a confined attempt
(`manager.confine=bwrap`). The Python and Bash VASP workflows in
*workflows-vasp* add the launch prefix automatically.

By default the persistent workdir is the result. Pass `--parameter
publish_data=true` to `httk job new` to also publish the files into `data/`
(below `data_prefix`).

## Building

Every package except Perl declares `[workflow.build]`. It is built and
registered for this platform class (`uname -sm`; Java bytecode has no platform
tag) when it is installed into a workspace, before a manager runs its jobs,
and rebuilt by name:

```console
httk workflow install --workspace WORKSPACE ./vasp-relax-c
httk workflow build --workspace WORKSPACE vasp.relax-c
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

A workflow is installed in a workspace before jobs of it are created;
`--install` installs (and builds) it first:

```console
httk job new --install --workflow 'git+https://github.com/httk/workflows-vasp-other-languages@<ref>#vasp-relax-c' --input structure=POSCAR
```

`<ref>` may be a commit, branch, or tag, or omitted for the default branch; it
is canonicalized to the full commit hash the repository is cloned at, and the
named subdirectory's `httk_workflow.toml` package is installed. Once installed,
its short name (e.g. `vasp.relax-c`) also resolves.

## Install as a plugin

```console
httk plugin install 'git+https://github.com/httk/workflows-vasp-other-languages'
```

installs all seven workflow packages listed in `httk_plugin.toml` at once on
this machine; each is still installed into a workspace (`httk job new
--install --workflow vasp.relax-c`) before its jobs are created.

## Testing

```console
make test
```

runs `pytest` on `tests/` against the installed *httk-workflow* and
*httk-workflow-vasp*. Each
language's end-to-end test installs (and so builds) its package into a
workspace, runs one relaxation job through a real task manager with the mock
VASP in `tests/mock_vasp.py`, and collects it; it is skipped when that
language's toolchain is missing. `HTTK_TEST_PROFILE=extended` also runs each
package with `publish_data`.
