# `httk workflow build` exports HTTK_WORKFLOW_LANGUAGES_DIR, the installed native SDK directory.
ifndef HTTK_WORKFLOW_LANGUAGES_DIR
$(error HTTK_WORKFLOW_LANGUAGES_DIR is not set; build with `httk workflow build` or set it to the installed httk/workflow/languages)
endif
SDK := $(HTTK_WORKFLOW_LANGUAGES_DIR)

.PHONY: all clean

all:
	mkdir -p classes
	javac --release 17 -Werror -Xlint:all -d classes $(SDK)/java/HttkWorkflow.java Relax.java

clean:
	rm -rf classes
