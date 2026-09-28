#!/usr/bin/env perl

use strict;
use warnings;

use lib $ENV{HTTK_WORKFLOW_PERL_API} // die "HTTK_WORKFLOW_PERL_API is not set; run this under httk-workflow\n";
use HttkWorkflow;

my @collect = qw(INCAR KPOINTS OUTCAR CONTCAR OSZICAR vasprun.xml vasp-run-report.json);

sub env_or {
    my ($name, $fallback) = @_;
    return defined($ENV{$name}) && $ENV{$name} ne '' ? $ENV{$name} : $fallback;
}

sub step_prepare {
    my ($attempt) = @_;
    if (!$attempt->stage_input('poscar', 'POSCAR', 'files/POSCAR')) {
        $attempt->fail('vasp.input_missing', 'the starting structure is not in this payload', 0);
        return 0;
    }
    $attempt->stage_input('incar', 'INCAR', 'files/INCAR');
    $attempt->runlog_note('prepared a relaxation');
    $attempt->advance('run', []);
    return 0;
}

sub step_run {
    my ($attempt) = @_;
    my $from_parameter = $attempt->parameter('vasp_command', '');
    my $command = $attempt->setting('vasp.command', $from_parameter);
    $command = '' unless defined($command);
    if ($command =~ /^\s*$/) {
        $attempt->fail(
            'vasp.command_missing',
            'no VASP command is configured: set it with '
                . "httk workspace settings set --key vasp.command --value '...' WORKSPACE, or set "
                . 'HTTK_VASP_COMMAND, or give the job a vasp_command parameter',
            0,
        );
        return 0;
    }

    my $timeout = $attempt->parameter('timeout', '86400');
    my @tokens = split /\s+/, $command;
    my @args = ('--timeout', $timeout, '--report', 'vasp-run-report.json', '--', @tokens);
    my $status = $attempt->run(\@args);
    if ($status == 0) {
        $attempt->state_set('classification', 'completed');
        $attempt->runlog_note('VASP completed');
        $attempt->advance('publish', []);
    } else {
        $attempt->fail('vasp.failed', "VASP did not complete (status $status)", 0);
    }
    return 0;
}

sub step_publish {
    my ($attempt) = @_;
    my $prefix = $attempt->parameter('data_prefix', 'vasp');
    my $data_dir = env_or('HTTK_WORKFLOW_DATA_DIR', '');
    for my $name (@collect) {
        next unless -f $name;
        $attempt->put($name, "$prefix/$name") if $data_dir ne '';
    }
    $attempt->runlog_note($data_dir ne '' ? 'published to transactional data' : 'kept the result in the workdir');
    $attempt->succeed();
    return 0;
}

my $runner = HttkWorkflow::Runner->new(
    workflow => 'vasp.relax-perl',
    steps => [qw(prepare run publish)],
);
$runner->step(prepare => \&step_prepare)
    ->step(run => \&step_run)
    ->step(publish => \&step_publish)
    ->main();
