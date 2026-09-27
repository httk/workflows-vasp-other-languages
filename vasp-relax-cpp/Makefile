# `httk workflow build` exports HTTK_WORKFLOW_LANGUAGES_DIR, the installed native SDK directory.
ifndef HTTK_WORKFLOW_LANGUAGES_DIR
$(error HTTK_WORKFLOW_LANGUAGES_DIR is not set; build with `httk workflow build` or set it to the installed httk/workflow/languages)
endif
SDK := $(HTTK_WORKFLOW_LANGUAGES_DIR)

# The C and C++ halves use their own language flags, then link together.
relax: relax.cpp $(SDK)/cpp/httk_workflow.hpp $(SDK)/c/httk_workflow.c $(SDK)/c/httk_workflow.h
	$(CC) -std=c99 -Wall -Wextra -c $(SDK)/c/httk_workflow.c -I$(SDK)/c -o httk_workflow_c.o
	$(CXX) -std=c++17 -Wall -Wextra -I$(SDK)/cpp -o relax relax.cpp httk_workflow_c.o

clean:
	rm -f relax httk_workflow_c.o
