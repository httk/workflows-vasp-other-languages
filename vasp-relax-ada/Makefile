# `httk workflow build` exports HTTK_WORKFLOW_NATIVE_API, the installed native SDK directory.
ifndef HTTK_WORKFLOW_NATIVE_API
$(error HTTK_WORKFLOW_NATIVE_API is not set; build with `httk workflow build` or set it to the installed httk/workflow/native)
endif
SDK := $(HTTK_WORKFLOW_NATIVE_API)

ADAFLAGS := -gnat2012 -gnatwa -gnatwe

relax: relax.adb relax_steps.adb relax_steps.ads $(SDK)/ada/httk_workflow.adb $(SDK)/ada/httk_workflow.ads $(SDK)/c/httk_workflow.c $(SDK)/c/httk_workflow.h
	$(CC) -std=c99 -c $(SDK)/c/httk_workflow.c -o httk_workflow_c.o
	gnatmake $(ADAFLAGS) -I$(SDK)/ada -o relax relax.adb -largs httk_workflow_c.o

clean:
	# The wildcards include relax_steps and all other Ada/GNAT intermediates.
	rm -f relax *.o *.ali b~*
