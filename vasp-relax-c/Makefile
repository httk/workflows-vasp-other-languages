# `httk workflow build` exports HTTK_WORKFLOW_NATIVE_API, the installed native SDK directory.
ifndef HTTK_WORKFLOW_NATIVE_API
$(error HTTK_WORKFLOW_NATIVE_API is not set; build with `httk workflow build` or set it to the installed httk/workflow/native)
endif
SDK := $(HTTK_WORKFLOW_NATIVE_API)

relax: relax.c $(SDK)/c/httk_workflow.c $(SDK)/c/httk_workflow.h
	$(CC) -std=c99 -Wall -Wextra -I$(SDK)/c -o relax relax.c $(SDK)/c/httk_workflow.c

clean:
	rm -f relax
