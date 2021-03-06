"""
Determines commands to be run in order to update the original directory and match
the state of the edit directory.
"""
from roamer.command import Command
from roamer.record import Record
from roamer.entry import Entry

class Engine(object):
    def __init__(self, original_dir, edit_dir):
        self.original_dir = original_dir
        self.edit_dir = edit_dir
        self.commands = []

    def compile_commands(self):
        self.compare_dirs()
        self.new_entries()
        self.handle_unknown_digests()
        self.save_copy_over_files_to_trash()

    def compare_dirs(self):
        for digest, original_entry in self.original_dir.entries.items():
            new_entries = self.edit_dir.find(digest)
            if new_entries is None:
                self.commands.append(Command('roamer-trash-copy', original_entry))
                continue
            found_original = False
            for new_entry in new_entries:
                if new_entry.name == original_entry.name:
                    found_original = True
                else:
                    self.commands.append(Command('cp', original_entry, new_entry))
            if not found_original:
                self.commands.append(Command('roamer-trash-copy', original_entry))

    def new_entries(self):
        add_blank_entries = self.edit_dir.find(None)
        if add_blank_entries:
            for entry in add_blank_entries:
                self.commands.append(Command('touch', entry))

    def handle_unknown_digests(self):
        unknown_digests = set(self.edit_dir.entries.keys()) - set(self.original_dir.entries.keys())

        for digest in filter(None, unknown_digests):
            record = Record(self.original_dir)
            outside_entry = record.entries.get(digest) or record.trash_entries.get(digest)
            if outside_entry is None:
                raise Exception('digest %s not found' % digest)

            for entry in self.edit_dir.find(digest):
                new_entry = Entry(entry.name, self.original_dir)
                self.commands.append(Command('cp', outside_entry, new_entry))

    def save_copy_over_files_to_trash(self):
        trash_entries = [c.first_entry for c in self.commands if c.cmd == 'roamer-trash-copy']
        copy_over_entires = [c.second_entry.name for c in self.commands if c.cmd == 'cp']
        for entry in trash_entries:
            if entry.name not in copy_over_entires:
                self.commands.append(Command('rm', entry))

    def commands_to_str(self):
        string_commands = [str(command) for command in sorted(self.commands)]
        # sort so that cp comes first.  Need to copy before removals happen
        return '\n'.join(string_commands)

    def run_commands(self):
        return [command.execute() for command in sorted(self.commands)]
