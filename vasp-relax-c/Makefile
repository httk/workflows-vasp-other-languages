# `httk workflow build` exports HTTK_WORKFLOW_LANGUAGES_DIR, the installed native SDK directory.
ifndef HTTK_WORKFLOW_LANGUAGES_DIR
$(error HTTK_WORKFLOW_LANGUAGES_DIR is not set; build with `httk workflow build` or set it to the installed httk/workflow/languages)
endif
SDK := $(HTTK_WORKFLOW_LANGUAGES_DIR)

relax: relax.c $(SDK)/c/httk_workflow.c $(SDK)/c/httk_workflow.h
	$(CC) -std=c99 -Wall -Wextra -I$(SDK)/c -o relax relax.c $(SDK)/c/httk_workflow.c

clean:
	rm -f relax
