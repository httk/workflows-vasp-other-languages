# `httk workflow build` exports HTTK_WORKFLOW_NATIVE_API, the installed native SDK directory.
ifndef HTTK_WORKFLOW_NATIVE_API
$(error HTTK_WORKFLOW_NATIVE_API is not set; build with `httk workflow build` or set it to the installed httk/workflow/native)
endif
SDK := $(HTTK_WORKFLOW_NATIVE_API)

# The two SDK halves are compiled with their own compilers: the Fortran standard
# flag is not valid for C, and vice versa, so the C source is compiled to an
# object with $(CC) and linked into the Fortran build with $(FC).
FC := gfortran
FFLAGS := -std=f2008 -Wall -Wextra

relax: relax.f90 $(SDK)/fortran/httk_workflow.f90 $(SDK)/c/httk_workflow.c $(SDK)/c/httk_workflow.h
	$(CC) -std=c99 -c $(SDK)/c/httk_workflow.c -o httk_workflow_c.o
	$(FC) $(FFLAGS) -o relax $(SDK)/fortran/httk_workflow.f90 relax.f90 httk_workflow_c.o

clean:
	rm -f relax httk_workflow_c.o httk_workflow.mod relax_steps.mod
