# `httk workflow build` exports HTTK_WORKFLOW_NATIVE_API, the installed native SDK directory.
ifndef HTTK_WORKFLOW_NATIVE_API
$(error HTTK_WORKFLOW_NATIVE_API is not set; build with `httk workflow build` or set it to the installed httk/workflow/native)
endif
SDK := $(HTTK_WORKFLOW_NATIVE_API)

.PHONY: all clean

all:
	mkdir -p classes
	javac --release 17 -Werror -Xlint:all -d classes $(SDK)/java/HttkWorkflow.java Relax.java

clean:
	rm -rf classes
