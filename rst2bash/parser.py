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
import os
import re
import yaml


import parsererr as ParserErr


# TODO(dbite): Remove CamelCasing.
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

    def __init__(self, startIndex=tuple(), endIndex=tuple()):

        self.startIndex = tuple(startIndex)
        self.endIndex = tuple(endIndex)

    def get_start_block(self, index):
        '''Returns the value of the start index.'''

        return self.startIndex[index]

    def get_end_block(self, index):
        '''Returns the value of the end index.'''

        return self.endIndex[index]

    def get_block(self, index):
        '''Returns the value of the block from the start and the end index.'''

        return (self.get_start_index(index), self.getEndindex(index))

    def get_start_index(self, block):
        '''Returns the index of the given block from the start index.'''

        if self._block_exists(block, self.startIndex):
            return self.startIndex.index(block)

        return False

    def get_end_index(self, block):
        '''Returns the index of the given block from the end index.'''

        if self._block_exists(block, self.endIndex):
            return self.endIndex.index(block)

        return False

    def get_index(self, block):
        '''Returns the index of the given block from both the indices.'''

        return (self.get_start_block(block), self.get_end_index(block))

    def _block_exists(self, block, index):
        """Returns true or false if the block exists."""

        return block in index

    def get_startindex_generator(self):
        """Returns a generator of startIndex."""

        return self._generator(self.startIndex)

    def get_endindex_generator(self):
        """Returns a generator of endIndex."""

        return self._generator(self.endIndex)

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

    def append(self, **kwargs):
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
        bashCommands = defaultdict(list)
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
            bashCommands[distro].append(bashcodelines)

        return bashCommands

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

    def extract_code(self, codeBlock, cmdType, distro, path):
        """Parse the rst block into command and extract metadata info.

        This method extracts all the metadata surrounding the given line of
        code and also detects the type of the code/config/inject before
        invoking the respective methods.
        """

        command = CodeBlock()

        # Simple helper function.
        def getdistro(distro):
            distro = distro.replace('.. only::', '').split('or')
            return [d.strip() for d in distro]
        distro = getdistro(distro) if distro else ["ubuntu", "obs", "rdo"]

        if path:
            path = path.replace('.. path', '').strip()

        command.append(distro=distro, path=path)

        if 'console' in cmdType:
            action = 'console'
            codeBlock = self._parse_code(codeBlock)
        elif 'apache' in cmdType:
            action = 'inject'
            codeBlock = self._parse_inject(codeBlock)
        elif 'ini' in cmdType or 'conf' in cmdType:
            action = 'config'
            codeBlock = self._parse_config(codeBlock)
        else:
            msg = "Invalid command type: %s" % cmdType
            raise ParserErr.InvalidCodeBlockError(msg)

        command.append(action=action, command=codeBlock)

        return command

# ------------------------------------------------------------------------------

    def _parse_inject(self, rstBlock):
        """Parse inject lines.

        These lines are usually configuration lines which are copy pasted or
        appended at the end of a file. Appending newlines with EOL for better
        visual appearance and easier BASH syntax generation.
        """

        return [rstBlock + "\nEOL\n"]

    def _parse_config(self, rstBlock):
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
        parsedConfig = list()

        for line in rstBlock.split('\n'):
            line = line.strip()
            if re.search('\[[a-zA-Z_]+\]', line):
                operator = line[1:-1]
            elif re.search('=', line) and not re.search('^#', line):
                line = operator + " " + line.replace("=", " ") + "\n"
                parsedConfig.append(line.strip())

        return parsedConfig

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

    def _parse_code(self, rstBlock):
        """Parse code lines.

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

        parsedCmds = list()

        if "mysql>" in rstBlock:
            rstBlock = rstBlock.replace("mysql>", ">")

        # Substitute HTML codes for '\' and '\n'
        rstBlock = rstBlock.replace("\\\n", "&#10&#10&#13")

        for index in re.finditer("[#\$>].*", rstBlock):

            cmd = rstBlock[index.start():index.end()].replace("&#10&#10&#13",
                                                              "\\\n")
            operator = self._get_bash_operator(cmd[0])
            parsedCmds.append(operator + cmd[1:].strip())

        return parsedCmds


# ------------------------------------------------------------------------------


class ExtractBlocks(object):
    """Creates required indices form the rst code."""

    def __init__(self, rstFile, bashPath):

        self.rstFile = self.get_file_contents(rstFile)
        self.blocks = None  # Lookup table.
        self.allBlocksIterator = None
        self.parseblocks = ParseBlocks()
        self.bashCode = list()
        bashFileName = os.path.basename(rstFile).replace('.rst', '.sh')
        self.bashPath = {distro: os.path.join(path, bashFileName)
                         for distro, path in bashPath.iteritems()}

    def __del__(self):
        """Proper handling of the file pointer."""

        self.filePointer.close()

    def _get_indices(self, regexStr):
        """Helper function to return a tuple containing indices.

        The indices returned contains the location of the given blocks matched
        by the regex string. Returns the (start, end) index for the same.
        """

        searchBlocks = re.compile(regexStr, re.VERBOSE)
        indices = [index.span()
                   for index in searchBlocks.finditer(self.rstFile)]

        return indices

    def get_file_contents(self, filePath):
        """Return the contents of the given file."""

        self.filePointer = open(filePath, 'r')

        return self.filePointer.read()

# ------------------------------------------------------------------------------

    def get_indice_blocks(self):
        """Should fetch regex strings from the right location."""

        # TODO(dbite): Populate the regex strings from a configuration file.
        # Regex string for extracting particular bits from RST file.
        # For some reason I want to keep the generic RegEX strings.
        # XXX(dbite): Figure out the index|indices confusing terms.
        searchAllBlocks = '''\.\.\s     # Look for '.. '
            (code-block::|only::|path)  # Look for required blocks
            [a-z\s/].*
            '''
        searchDistroBlocksStart = '''\.\.\sonly::
            [\sa-z].*                               # For matching all distros.
            '''
        searchDistroBlocksEnd = '''\.\.\sendonly\\n'''      # Match end blocks.

        searchCodeBlocksStart = '''\.\.\scode-block::   # Look for code block
            \s                                      # Include whitespace
            (?!end)                                 # Exclude code-block:: end
            (?:[a-z])*                              # Include everything else.
        '''
        searchCodeBlocksEnd = '''\.\.\send\\n'''    # Look for .. end
        searchPath = '''\.\.\spath\s.*'''           # Look for .. path

        allBlocks = BlockIndex(self._get_indices(searchAllBlocks))
        distroBlocks = BlockIndex(self._get_indices(searchDistroBlocksStart),
                                  self._get_indices(searchDistroBlocksEnd))
        codeBlocks = BlockIndex(self._get_indices(searchCodeBlocksStart),
                                self._get_indices(searchCodeBlocksEnd))
        pathBlocks = BlockIndex(self._get_indices(searchPath))

        # Point to the blocks from a dictionary to create sensible index.
        self.blocks = {'distroBlock': distroBlocks,
                       'codeBlock': codeBlocks,
                       'pathBlock': pathBlocks,
                       'allBlock': allBlocks
                       }

# ------------------------------------------------------------------------------
#   Recursive Generator Pattern.
# ------------------------------------------------------------------------------

    def extract_codeblocks(self):
        """Initialize the generator object and start the initial parsing."""

        # Generate all blocks iterator
        self.allBlocksIterator = \
            self.blocks['allBlock'].get_startindex_generator()

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

        for blockName in 'codeBlock', 'distroBlock', 'pathBlock':
            blockIndex = self.blocks[blockName].get_start_index(allblock)
            if blockIndex is not False:
                return blockName, blockIndex
        else:
            msg = "Invalid block name: %s" % blockName
            raise ParserErr.InvalidBlockError(msg)

    # Helper function for recursive-generator pattern.
    def _extractblocks(self, distro=None, path=None, distroEnd=None):
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
            blockName, blockIndex = self._block_lookup(
                self.allBlocksIterator.next())
        except StopIteration:
            return

        block = self.blocks[blockName]

        # TODO(dbite): Implement a mechanism for locating the exact location in
        #              the rst file at the current recursive depth. This
        #              information should then be logged and passed via. the
        #              exception traceback. Save required vars. in a global
        #              variable.
        if distroEnd < block.get_start_block(blockIndex)[0]:
            distro = None

        if 'codeBlock' in blockName:
            # Extract Code Block
            # Use path & distro variables.
            indexStart = block.get_start_block(blockIndex)
            indexEnd = block.get_end_block(blockIndex)
            codeBlock = self.rstFile[indexStart[1]:indexEnd[0]].strip()
            cmdType = self.rstFile[indexStart[0]:indexStart[1]]
            self.bashCode.append(
                self.parseblocks.extract_code(codeBlock,
                                              cmdType,
                                              distro,
                                              path))
            self._extractblocks(distro=distro, distroEnd=distroEnd)

        elif 'pathBlock' in blockName:
            # Get path & recurse, the next one should be CodeBlock.
            pathIndex = block.get_start_block(blockIndex)
            path = self.rstFile[pathIndex[0]:pathIndex[1]]
            self._extractblocks(distro=distro, path=path, distroEnd=distroEnd)

        elif 'distroBlock' in blockName:
            # Get distro & recurse
            distroStart = block.get_start_block(blockIndex)
            distro = self.rstFile[distroStart[0]:distroStart[1]]
            distroEnd = block.get_end_block(blockIndex)[1]
            self._extractblocks(distro=distro, distroEnd=distroEnd)

        return

# ------------------------------------------------------------------------------

    def get_bash_code(self):
        """Returns bashCode which is a list containing <CodeBlock>'s."""

        return self.bashCode

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

        for code in self.bashCode:
            codeLines = code.generate_code()
            for distro, codeLine in codeLines.iteritems():
                commands[distro] += newline.join(codeLine)

        for distro, command in commands.iteritems():
            ExtractBlocks.write_to_file(self.bashPath[distro], command)

        return True

# ------------------------------------------------------------------------------

if __name__ == '__main__':

    # TODO(dbite): Cleanup the main function.
    with open("rst2bash/config/parser_config.yaml", 'r') as ymlfile:
        cfg = yaml.load(ymlfile)

    cwd = os.getcwd()
    rst_path = os.path.join(cwd, cfg['rst_path'])
    rst_files = cfg['rst_files']
    bash_path = {distro: os.path.join(cwd, path)
                 for distro, path in cfg['bash_path'].iteritems()}

    for path_value in bash_path.itervalues():

        if not os.path.exists(path_value):
            os.mkdir(path_value)

    for rst_file in rst_files:

        parser_message = "\nError: XXX: Failed to parse %s to bash.\n\t    - "

        try:
            rst_file_path = os.path.join(rst_path, rst_file)
            code_blocks = ExtractBlocks(rst_file_path, bash_path)
            code_blocks.get_indice_blocks()
            code_blocks.extract_codeblocks()
            bashCode = code_blocks.get_bash_code()

            if not code_blocks.write_bash_code():
                msg = "Could not write to bash: %s" % rst_file_path
                raise ParserErr.Rst2BashError(msg)

        except (ParserErr.InvalidCodeBlockError,
                ParserErr.InvalidOperatorError,
                ParserErr.InvalidBlockError,
                ParserErr.MissingTagsError) as ex:
            parser_message = parser_message + repr(ex) + "\n"
        except ParserErr.Rst2BashError as ex:
            pass
        else:
            parser_message = "Success :): parsed %s to bash. :D"
        finally:
            print(parser_message % rst_file)
