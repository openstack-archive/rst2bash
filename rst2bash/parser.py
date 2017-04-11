#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.


from collections import defaultdict
import logging
import os
import re
import yaml


import parsererr as ParserErr


def configure_logging(log_file):
    """Configure root logger"""
    logger = logging.getLogger()

    logger.setLevel(logging.DEBUG)

    # Level name colored differently (both console and file)
    logging.addLevelName(logging.WARNING, '\x1b[0;33m%s\x1b[0m' %
                         logging.getLevelName(logging.WARNING))
    logging.addLevelName(logging.ERROR, '\x1b[0;31m%s\x1b[0m' %
                         logging.getLevelName(logging.ERROR))

    # Configure console logging
    console_log_handler = logging.StreamHandler()
    console_log_handler.setLevel(logging.INFO)
    # All console messages are the same color (except with colored level names)
    console_formatter = logging.Formatter('\x1b[0;32m%(levelname)s'
                                          '\t%(message)s\x1b[0m')
    console_log_handler.setFormatter(console_formatter)
    logger.addHandler(console_log_handler)

    # Configure log file
    if os.path.isfile(log_file):
        os.remove(log_file)

    file_log_handler = logging.FileHandler(log_file)
    file_log_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(process)s %(asctime)s.%(msecs)03d'
                                       ' %(name)s %(levelname)s %(message)s',
                                       datefmt="%H:%M:%S")
    file_log_handler.setFormatter(file_formatter)
    logger.addHandler(file_log_handler)

    logger.debug("Root logger configured.")


# ------------------------------------------------------------------------------
#   Custom data-types.
# ------------------------------------------------------------------------------
class BlockIndex(object):
    """Creates indices which describes the location of blocks in rst file.

    These indices describe the start and end location of the strings in the rst
    file. Different indices used to parse the file are:

        AllBlocks: Contains sequential index values for all required blocks.
        CodeBlocks: Contains index values for blocks containing code.
        PathBlocks: Contains index values for blocks containing path.
        DistroBlocks: Contains index values for blocks containing OS.

    These indices should provide the location to extract given blocks from the
    rst files. This class additionally provides various functionalities to
    easily carry out different tasks like iteration and more.
    """

    def __init__(self, start_index=tuple(), end_index=tuple()):

        self.start_index = tuple(start_index)
        self.end_index = tuple(end_index)

    def get_start_block(self, index):
        '''Returns the value of the start index.'''

        return self.start_index[index]

    def get_end_block(self, index):
        '''Returns the value of the endIndex.'''

        return self.end_index[index]

    def get_block(self, index):
        '''Returns the value of the block from the start and the endIndex.'''

        return (self.get_start_index(index), self.get_end_index(index))

    def get_start_index(self, block):
        '''Returns the index of the given block from the startIndex.'''

        if self._block_exists(block, self.start_index):
            return self.start_index.index(block)

        return False

    def get_end_index(self, block):
        '''Returns the index of the given block from the endIndex.'''

        if self._block_exists(block, self.end_index):
            return self.end_index.index(block)

        return False

    def get_index(self, block):
        '''Returns the index of the given block from both the indices.'''

        return (self.get_start_block(block), self.get_end_index(block))

    def _block_exists(self, block, index):
        """Returns true or false if the block exists."""

        return block in index

    def get_start_index_generator(self):
        """Returns a generator of startIndex."""

        return self._generator(self.start_index)

    def get_end_index_generator(self):
        """Returns a generator of endIndex."""

        return self._generator(self.end_index)

    def _generator(self, index):
        """Create a generator of the given index."""
        for i in index:
            yield i


class CodeBlock(object):
    """CodeBlock acts as a custom data-structure.

    CodeBlock defines a rst block which contains a one or more lines of code or
    configuration files. Additionally CodeBlocks also organizes metadata about
    the rst block which could be as simple as the prompt/user or the path of
    the configuration file.

    CodeBlock at the end of the day should contain the following keys and
    values extracted and parsed from the rst files.

    commands = { <key: value_type, possible values, description>

    distro: <str>, [ubuntu|rdo|obs|debian] or [all],
                This tag specifies the distro which could be a combination of
                different distros or all distros.
    action: <str>, [console|config|inject],
                This could either be a bash command, configuration or file
                inject.
    type: <str>, [ini|conf|apache|...],
                Describes the content of the command. It is fetched from the
                rst .. code-block|.. distro tag.
    path: <str>|<os.path>,
                If it is a config or inejct, the path of the given file. For
                commands, the path to run the command at.
    command: <list>, [<str>,<str>],
                Describes the command itself. This command along with the
                metadata provides easily BASHable datastructure.
    output_file: <dict>, {distro: path},
                Describes the absolute path of the given bash file where the
                command should be written.
    }

    This class provides the datastructure along with methods to consume various
    actions required to fill the datastructure and traverse through it.
    """

    def __init__(self):

        self.command = {}

    def update(self, **kwargs):
        """Add or update values to the datastructure."""

        self.command.update(kwargs)

    def __dict__(self):

        return self.command

    def generate_code(self):
        """Generate BASH command with it's metadata.

        This method should sensibly traverse through the command dictonary and
        generate and return the BASH code. Also return the distribution name.
        """

        command_wrapper = ''
        bashcodelines = ''
        bash_commands = defaultdict(list)
        newline = '\n'
        action = self.command['action']

        path = self.command['path']
        if path:
            bashcodelines = '{0}conf={1}{0}'.format(newline, path)

        if 'config' in action:
            command_wrapper = 'iniset_sudo $conf '
        elif 'inject' in action:
            command_wrapper = '{0}cat<< INJECT | sudo tee -a $conf{0}'
            command_wrapper = command_wrapper.format(newline)

        for codeline in self.command['command']:
            bashcodelines += command_wrapper + codeline + newline

        for distro in self.get_distro():
            bash_commands[distro].append(bashcodelines)

        return bash_commands

    def get_distro(self):
        """Return the distribution."""

        return self.command['distro']


# ------------------------------------------------------------------------------
# Parser Logic.
# ------------------------------------------------------------------------------
class ParseBlocks(object):
    """Convert RST block to BASH code.

    Logic to convert a given RST block into BASH. This class should extract
    given code from the RST block and consume the CodeBlocks datastructure to
    preserve the metadata along with the code.

    ParseBlocks has three logical sections:

        - Metadata extraction and code type detection.
        - Parsing Bash/Config/Inject content.
        - Assembling all the information in CodeBlocks format.
    """

    def extract_code(self, code_block, cmd_type, distro, path):
        """Parse the rst block into command and extract metadata info.

        This method extracts all the metadata surrounding the given line of
        code and also detects the type of the code/config/inject before
        invoking the respective methods.
        """

        command = CodeBlock()

        def getdistro(distro):
            """Return distros named in code block title"""
            distro = distro.replace('.. only::', '').split('or')
            return [d.strip() for d in distro]
        # Having the list of distros hardcoded here is not ideal. The list
        # could be generated from openstack-manuals' tox.ini or by searching
        # for all named distros in all '.. only::' titles, or it could be part
        # of the configuration file.
        distro = getdistro(distro) if distro else ["debian", "ubuntu", "obs",
                                                   "rdo"]

        if path:
            path = path.replace('.. path', '').strip()

        command.update(distro=distro, path=path)

        if 'console' in cmd_type:
            action = 'console'
            code_block = self._parse_code(code_block)
        elif 'apache' in cmd_type:
            action = 'inject'
            code_block = self._parse_inject(code_block)
        elif 'ini' in cmd_type or 'conf' in cmd_type:
            action = 'config'
            code_block = self._parse_config(code_block)
        else:
            msg = "Invalid command type: %s" % cmd_type
            raise ParserErr.InvalidCodeBlockError(msg)

        command.update(action=action, command=code_block)

        return command

# ------------------------------------------------------------------------------

    def _parse_inject(self, rst_block):
        """Parse inject lines.

        These lines are usually configuration lines which are copy pasted or
        appended at the end of a file. Appending newlines with EOL for better
        visual appearance and easier BASH syntax generation.
        """

        return [rst_block + "\nEOL\n"]

    def _parse_config(self, rst_block):
        """Parse configuration files.

        Configuration file modifications, which mostly involves setting or
        resetting given variables and parameters. This method:

            - Detects the configuration sections ``[section]``.
            - Parses the following lines under this section iteratively.
            - Go to step one if more lines.
            - Generate a list of configuration lines along with it's section
              in training-labs friendly format.
            - Also some syntax niceness sprinkled on top.
        """

        operator = ''

        # Only works for a specific sequence of configuration options.
        parsed_config = list()

        for line in rst_block.split('\n'):
            line = line.strip()
            if re.search(r'\[[a-zA-Z0-9_]+\]', line):
                operator = line[1:-1]
            elif re.search('=', line) and not re.search('^#', line):
                line = operator + " " + line.replace("=", " ") + "\n"
                parsed_config.append(line.strip())

        return parsed_config

    @staticmethod
    def _get_bash_operator(operator):
        """Helper function to convert the operator to its equivalent syntax.

        # --> root --> sudo ...
        $ --> noroot --> ...
        > --> mysql --> mysql_exec ...
        """

        if "#" in operator:
            operator = "sudo "
        elif "$" in operator:
            operator = ""
        elif ">" in operator:
            operator = "mysql_exec "
        else:
            msg = "Invalid operator: %s" % operator
            raise ParserErr.InvalidOperatorError(msg)

        return operator

    def _parse_code(self, rst_block):
        r"""Parse code lines.

        Code-blocks containing bash code (console|mysql) are sent here. These
        are bash code or mysql etc. which are to be formatted into proper bash
        format.

         - Detects type of code, replace `mysql>` with `>` if detected.
         - Replace line continuation `asdb \` with equivalent HTML codes
           for `\` and `\n` to properly parse multi-line commands.
         - Iterate through all the code lines which are easily detected using
           the operator syntax.
         - Replace the HTML codes to it's respective ASCII/UNICODE equivalent.
        """

        parsed_cmds = list()

        if "mysql>" in rst_block:
            rst_block = rst_block.replace("mysql>", ">")

        # Substitute HTML codes for '\' and '\n'
        rst_block = rst_block.replace("\\\n", "&#10&#10&#13")

        for index in re.finditer(r"[#\$>].*", rst_block):

            cmd = rst_block[index.start():index.end()].replace("&#10&#10&#13",
                                                               "\\\n")
            operator = self._get_bash_operator(cmd[0])
            parsed_cmds.append(operator + cmd[1:].strip())

        return parsed_cmds


# ------------------------------------------------------------------------------


class ExtractBlocks(object):
    """Creates required indices form the rst code."""

    def __init__(self, rst_file, bash_path):

        logger.info("Processing %s.", os.path.basename(rst_file))
        self.rst_file = self.get_file_contents(rst_file)
        self.blocks = None  # Lookup table.
        self.all_blocks_iterator = None
        self.parseblocks = ParseBlocks()
        self.bash_code = list()
        bash_file_name = os.path.basename(rst_file).replace('.rst', '.sh')
        logger.debug("bash_path %s", bash_path)
        self.bash_path = {distro: os.path.join(path, bash_file_name)
                          for distro, path in bash_path.iteritems()}
        logger.debug("ExtractBlocks __init__ bash_path %s", self.bash_path)

    def __del__(self):
        """Proper handling of the file pointer."""

        self.file_pointer.close()

    def index_to_line_no(self, index):
        """Return line number, given index into string"""
        # Count newline characters (no newline -> line number 1)
        return self.rst_file.count("\n", 0, index) + 1

    def _get_indices(self, regex_str):
        """Helper function to return a tuple containing indices.

        The indices returned contains the location of the given blocks matched
        by the regex string. Returns the (start, end) index for the same.
        """

        search_blocks = re.compile(regex_str, re.VERBOSE)
        indices = [index.span()
                   for index in search_blocks.finditer(self.rst_file)]

        logger.debug("_get_indices %s %s", regex_str, indices)
        return indices

    def get_start_end_block(self, search_start, search_end):
        """Search file for start and stop codes

        Search for start and stop codes (e.g., "only", "endonly") and
        report an error if the numbers for both don't match.
        """
        start = self._get_indices(search_start)
        end = self._get_indices(search_end)

        # Log information on the indices we received
        msg = "get_start_end_block start/end mismatch:\n"
        msg += "    regex start: {}\n".format(search_start)
        msg += "    regex end:   {}\n".format(search_end)
        report = {}
        for ii in start:
            report[self.index_to_line_no(ii[0])] = "start block"
        for ii in end:
            report[self.index_to_line_no(ii[0])] = "end block  "
        for ii in sorted(report):
            msg += "    {} (line {})\n".format(report[ii], ii)
        if len(start) == len(end):
            logger.debug(msg)
        else:
            logger.error(msg)

        return start, end

    def get_file_contents(self, file_path):
        """Return the contents of the given file."""

        self.file_pointer = open(file_path, 'r')

        return self.file_pointer.read()

# ------------------------------------------------------------------------------

    def get_indice_blocks(self):
        """Should fetch regex strings from the right location."""

        # TODO(dbite): Populate the regex strings from a configuration file.
        # Regex string for extracting particular bits from RST file.
        # For some reason I want to keep the generic RegEX strings.
        # XXX(dbite): Figure out the index|indices confusing terms.
        search_all_blocks = r'''\.\.\s     # Look for '.. '
            (code-block::|only::|path)  # Look for required blocks
            [a-z\s/].*
            '''
        search_distro_blocks_start = r'''\.\.\sonly::
            [\sa-z].*                               # For matching all distros.
            '''
        search_distro_blocks_end = r'''\.\.\sendonly\n'''    # Match end block

        search_code_blocks_start = r'''\.\.\scode-block::   # Match code block
            \s                                      # Include whitespace
            (?!end)                                 # Exclude code-block:: end
            (?:[a-z])*                              # Include everything else.
        '''
        search_code_blocks_end = r'''\.\.\send\n'''    # Look for .. end
        search_path = r'''\.\.\spath\s.*'''            # Look for .. path

        all_blocks = BlockIndex(self._get_indices(search_all_blocks))

        start_index, end_index = self.get_start_end_block(
            search_distro_blocks_start, search_distro_blocks_end)
        distro_blocks = BlockIndex(start_index, end_index)

        start_index, end_index = self.get_start_end_block(
            search_code_blocks_start, search_code_blocks_end)
        code_blocks = BlockIndex(start_index, end_index)

        path_blocks = BlockIndex(self._get_indices(search_path))

        # Point to the blocks from a dictionary to create sensible index.
        self.blocks = {'distroBlock': distro_blocks,
                       'codeBlock': code_blocks,
                       'pathBlock': path_blocks,
                       'allBlock': all_blocks}

# ------------------------------------------------------------------------------
#   Recursive Generator Pattern.
# ------------------------------------------------------------------------------

    def extract_codeblocks(self):
        """Initialize the generator object and start the initial parsing."""

        # Generate all blocks iterator
        self.all_blocks_iterator = \
            self.blocks['allBlock'].get_start_index_generator()

        try:
            self._extractblocks()
        except IndexError as err:
            raise ParserErr.MissingTagsError(err)

    # Helper function for quick lookup from the blocks lookup table.
    def _block_lookup(self, allblock):
        """Block Lookup Helper Function.

        Look for the block in blocks and return the name and index of the
        location of the block.
        """

        for block_name in 'codeBlock', 'distroBlock', 'pathBlock':
            block_index = self.blocks[block_name].get_start_index(allblock)
            if block_index is not False:
                return block_name, block_index
        else:
            msg = "Invalid block name: %s" % block_name
            raise ParserErr.InvalidBlockError(msg)

    # Helper function for recursive-generator pattern.
    def _extractblocks(self, distro=None, path=None, distro_end=None):
        """Recursive function to sequentially parse the RST file.

        This method deals with traversing through the given RST file by using
        the indices generated using regex. These indices indicate the location
        of different chunks of blocks and also the distribution for the same.

        AllBlocks provides the location of all the blocks and is used to
        recurse and give the next block location. This block can either be
        CodeBlock, PathBlock or DistroBlock. The lookup table provides the
        information about which block a given index points to and fetches
        the equivalent end index. This allows further calls to ParseBlocks
        class to process the extracted chunk of code in the correct way.

        Using recursion is more efficient as compared to iteration. It
        simplifies the implementation logic, performance and efficiency. This
        also allows the parsing to be accomplished with minimal variables and
        eliminates need for keeping track, toggle flags and complicated code
        which is hard to debug and understand.
        """

        try:
            block_name, block_index = self._block_lookup(
                self.all_blocks_iterator.next())
        except StopIteration:
            return

        block = self.blocks[block_name]

        # TODO(dbite): Implement a mechanism for locating the exact location in
        #              the rst file at the current recursive depth. This
        #              information should then be logged and passed via. the
        #              exception traceback. Save required vars. in a global
        #              variable.
        if distro_end < block.get_start_block(block_index)[0]:
            distro = None

        if 'code_block' in block_name:
            # Extract Code Block
            # Use path & distro variables.
            index_start = block.get_start_block(block_index)
            index_end = block.get_end_block(block_index)
            code_block = self.rst_file[index_start[1]:index_end[0]].strip()
            cmd_type = self.rst_file[index_start[0]:index_start[1]]
            self.bash_code.append(
                self.parseblocks.extract_code(code_block,
                                              cmd_type,
                                              distro,
                                              path))
            self._extractblocks(distro=distro, distro_end=distro_end)

        elif 'pathBlock' in block_name:
            # Get path & recurse, the next one should be CodeBlock.
            path_index = block.get_start_block(block_index)
            path = self.rst_file[path_index[0]:path_index[1]]
            self._extractblocks(distro=distro,
                                path=path,
                                distro_end=distro_end)

        elif 'distroBlock' in block_name:
            # Get distro & recurse
            distro_start = block.get_start_block(block_index)
            distro = self.rst_file[distro_start[0]:distro_start[1]]
            distro_end = block.get_end_block(block_index)[1]
            self._extractblocks(distro=distro, distro_end=distro_end)

        return

# ------------------------------------------------------------------------------

    @staticmethod
    def write_to_file(path, value):
        """Static method to write given content to the file."""

        # TODO(dbite): Implement a file handler class.
        with open(path, 'w') as fp:
            fp.write(value)

    def write_bash_code(self):
        """Writes bash code to file."""

        commands = defaultdict(str)

        newline = "\n"

        for code in self.bash_code:
            code_lines = code.generate_code()
            for distro, code_line in code_lines.iteritems():
                commands[distro] += newline.join(code_line)

        for distro, command in commands.iteritems():
            ExtractBlocks.write_to_file(self.bash_path[distro], command)


# ------------------------------------------------------------------------------


if __name__ == '__main__':

    # TODO(dbite): Cleanup the main function.
    with open("rst2bash/config/parser_config.yaml", 'r') as ymlfile:
        cfg = yaml.load(ymlfile)

    configure_logging(cfg['log_file'])
    logger = logging.getLogger()

    cwd = os.getcwd()
    logger.debug("cwd %s", cwd)

    rst_path = os.path.join(cwd, cfg['rst_path'])
    logger.debug("rst_path %s", rst_path)

    rst_files = cfg['rst_files']
    logger.debug("rst_files %s", rst_files)

    bash_path = {distro: os.path.join(cwd, path)
                 for distro, path in cfg['bash_path'].iteritems()}
    logger.debug("bash_path %s", bash_path)

    for path_value in bash_path.itervalues():

        if not os.path.exists(path_value):
            os.mkdir(path_value)

    for rst_file in rst_files:

        try:
            rst_file_path = os.path.join(rst_path, rst_file)
            code_blocks = ExtractBlocks(rst_file_path, bash_path)
            code_blocks.get_indice_blocks()
            code_blocks.extract_codeblocks()

            code_blocks.write_bash_code()

        except (ParserErr.InvalidCodeBlockError,
                ParserErr.InvalidOperatorError,
                ParserErr.InvalidBlockError,
                ParserErr.MissingTagsError) as ex:
            logger.error(repr(ex))

    logger.info("")
    logger.info("Output written to:")
    for distro in bash_path:
        logger.info(bash_path[distro])
