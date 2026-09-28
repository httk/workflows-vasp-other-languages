/*
 * One VASP relaxation, authored in C: the same three-step shape as the Bash
 * runner of vasp.relax-bash in https://github.com/httk/workflows-vasp, built on
 * the native C SDK.
 *
 *   prepare  stage the payload POSCAR (and INCAR if present) into the workdir
 *   run      run the configured VASP command and classify what it did
 *   publish  copy the finished calculation into the job's transactional data
 *
 * Every httk_workflow_* call reaches the same implementation the Python and Bash
 * SDKs do, so this runner is mock-vasp compatible and publishes the same bytes.
 * Build it with the Makefile beside this file:
 *
 *     make
 *
 * See tests/mock_vasp.py for a stand-in VASP, and README.md for the whole flow.
 */

#define _POSIX_C_SOURCE 200809L

#include "httk_workflow.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* The files a finished relaxation publishes, if the run produced them. */
static const char *const COLLECT[] = {
    "INCAR", "KPOINTS", "OUTCAR", "CONTCAR", "OSZICAR", "vasprun.xml", "vasp-run-report.json", NULL,
};

static int step_prepare(void) {
    if (httk_workflow_stage_input("poscar", "POSCAR", "files/POSCAR") != HTTK_WORKFLOW_OK) {
        httk_workflow_fail("vasp.input_missing", "the starting structure is not in this payload", NULL);
        return 0;
    }
    /* An INCAR is optional; the mock VASP reads only the POSCAR. */
    httk_workflow_stage_input("incar", "INCAR", "files/INCAR");

    httk_workflow_runlog_note("prepared a relaxation");
    httk_workflow_advance("run", NULL);
    return 0;
}

static int step_run(void) {
    int status;
    char *from_parameter = httk_workflow_parameter("vasp_command", "", &status);
    char *command = httk_workflow_setting("vasp.command", from_parameter != NULL ? from_parameter : "", &status);
    free(from_parameter);
    if (command == NULL || *command == '\0') {
        free(command);
        httk_workflow_fail("vasp.command_missing",
                           "no VASP command is configured: set it with "
                           "httk workspace settings set --key vasp.command --value '...' WORKSPACE, or set "
                           "HTTK_VASP_COMMAND, or give the job a vasp_command parameter",
                           NULL);
        return 0;
    }

    char *timeout = httk_workflow_parameter("timeout", "86400", &status);

    /* The resolved command is one argv string; split it on whitespace, the way
     * the Bash runner leaves it unquoted for the shell to word-split. There can
     * be no more tokens than characters, so size the array for the worst case
     * once and never grow (nor silently truncate) it. */
    const char *fixed[] = {"--timeout", timeout != NULL ? timeout : "86400", "--report", "vasp-run-report.json", "--"};
    size_t fixed_n = sizeof fixed / sizeof fixed[0];
    size_t capacity = fixed_n + strlen(command) + 1;
    const char **args = malloc((capacity + 1) * sizeof *args);
    size_t n = 0;
    if (args != NULL) {
        for (size_t i = 0; i < fixed_n; i++) {
            args[n++] = fixed[i];
        }
        for (char *token = strtok(command, " \t"); token != NULL; token = strtok(NULL, " \t")) {
            args[n++] = token;
        }
        args[n] = NULL;
    }

    int run_status = args != NULL ? httk_workflow_run(args) : HTTK_WORKFLOW_REFUSED;
    free(args);
    free(timeout);
    free(command);

    if (run_status == 0) {
        httk_workflow_state_set("classification", "completed");
        httk_workflow_runlog_note("VASP completed");
        httk_workflow_advance("publish", NULL);
    } else {
        char message[96];
        snprintf(message, sizeof message, "VASP did not complete (status %d)", run_status);
        httk_workflow_fail("vasp.failed", message, NULL);
    }
    return 0;
}

static int step_publish(void) {
    int status;
    char *prefix = httk_workflow_parameter("data_prefix", "vasp", &status);
    const char *data_dir = getenv("HTTK_WORKFLOW_DATA_DIR");
    for (size_t i = 0; COLLECT[i] != NULL; i++) {
        if (!httk_file_exists(COLLECT[i])) {
            continue;
        }
        if (data_dir != NULL && *data_dir != '\0' && prefix != NULL) {
            char *destination = httk_join_path(prefix, COLLECT[i]);
            if (destination != NULL) {
                char *operation = httk_workflow_put(COLLECT[i], destination, &status);
                free(operation);
                free(destination);
            }
        }
    }
    httk_workflow_runlog_note(data_dir != NULL && *data_dir != '\0' ? "published to transactional data"
                                                                    : "kept the result in the workdir");
    httk_workflow_succeed();
    free(prefix);
    return 0;
}

int main(int argc, char **argv) {
    static const httk_workflow_step steps[] = {
        {"prepare", step_prepare},
        {"run", step_run},
        {"publish", step_publish},
    };
    if (httk_workflow_runner("vasp.relax-c", steps, sizeof steps / sizeof steps[0]) != 0) {
        return 2;
    }
    return httk_workflow_main(argc, argv);
}
