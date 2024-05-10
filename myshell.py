#! /usr/bin/env python3

import os
import sys

DEFAULT_PROMPT = "$ "
QUIT_COMMAND = "exit"


class MiniShell:
    def __init__(self):
        self.prompt = os.environ.get("PS1", DEFAULT_PROMPT)

    def start(self):
        try:
            while True:
                command_line = input(self.prompt).strip()
                self.execute_command(command_line)
        except EOFError:
            print("End of input file reached. Exiting the shell.")
            
    def change_directory(self, path):
        try:
            os.chdir(path)
        except OSError as e:
            print(e.strerror, file=sys.stderr)

    def execute_command(self, command_line):
        if command_line == QUIT_COMMAND:
            quit()
        elif "|" in command_line:
            self.handle_pipe(command_line)
        elif "<" in command_line:
            self.handle_input_redirection(command_line)
        elif ">" in command_line:
            self.handle_output_redirection(command_line)
        elif command_line.startswith("echo"):
            self.handle_echo(command_line)
        elif command_line.startswith("cd"):
            self.handle_cd(command_line)
        else:
            self.run_process(command_line)

    def run_process(self, command_line):
        run_foreground = True
        if command_line and command_line[-1] == "&":
            command_line = command_line[:-1]
            run_foreground = False

            arguments = command_line.split()
            if arguments and arguments[0] == "cd":
                self.change_directory(arguments[-1])
            else:
                self.execute_command_in_child(arguments, run_foreground)

    def execute_command_in_child(self, arguments, run_foreground=True):
        process_id = os.fork()
        if not process_id:
            try:
                os.execvp(arguments[0], arguments)
            except FileNotFoundError:
                print(f"Couldn't find command '{arguments[0]}'", file=sys.stderr)
            sys.exit(1)
        else:
            if run_foreground:
                self.wait_for_child_process()

    def wait_for_child_process(self):
        exit_info = os.wait()
        if exit_info[1]:
            print(f"Program terminated: exit code {exit_info[1]}")

    def handle_pipe(self, command_line):
        commands = command_line.split("|")
        write_arguments = commands[0].strip().split()
        read_arguments = commands[1].strip().split()
        read_fd, write_fd = os.pipe()
        self.execute_pipe_commands(write_arguments, read_arguments, read_fd, write_fd)

    def execute_pipe_commands(self, write_arguments, read_arguments, read_fd, write_fd):
        read_process_id = os.fork()
        if not read_process_id:
            os.dup2(read_fd, sys.stdin.fileno())
            os.close(write_fd)
            self.execute_command_in_child(read_arguments, False)
        else:
            os.dup2(write_fd, sys.stdout.fileno())
            os.close(read_fd)
            self.execute_command_in_child(write_arguments, True)

    def handle_echo(self, command_line):
        parts = command_line.split(" ", 1)
        if len(parts) == 1:
            print("")  # Just print a newline for 'echo' command without arguments
        else:
            print(parts[1])

    def handle_input_redirection(self, command_line):
        parts = command_line.split("<")
        arguments = parts[0].strip().split()
        filename = parts[1].strip()
        file_descriptor = os.open(filename, os.O_RDONLY)
        os.dup2(file_descriptor, sys.stdin.fileno())
        self.execute_command_in_child(arguments)

    def handle_output_redirection(self, command_line):
        parts = command_line.split(">")
        arguments = parts[0].strip().split()
        filename = parts[1].strip()
        file_descriptor = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
        saved_stdout = os.dup(sys.stdout.fileno())  # Save the original stdout
        os.dup2(file_descriptor, sys.stdout.fileno())
        os.close(file_descriptor)  # Close the file descriptor for the output file
        self.execute_command_in_child(arguments)
        os.dup2(saved_stdout, sys.stdout.fileno())  # Restore the original stdout
        os.close(saved_stdout)  # Close the duplicated stdout


if __name__ == "__main__":
    shell = MiniShell()
    shell.start()
