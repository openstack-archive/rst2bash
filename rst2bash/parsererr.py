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


class Rst2BashError(Exception):
    """Base class for exceptions for Rst2Bash module."""

    pass


class InvalidBlockError(Rst2BashError):
    """Error describing possible sphinx blocks but invalid for rst2bash."""

    pass


class MissingTagsError(Rst2BashError):
    """Error describing missing tags, especially rst2bash specific end tags."""

    pass


class NestedDistroBlocksError(Rst2BashError):
    """Error describing nested distribution blocks."""

    def __init__(self, *args, **kwargs):
        Rst2BashError.__init__(self, *args, **kwargs)


class PathNotFoundError(Rst2BashError):
    """Error describing missing path for certain commands (ex: config)."""

    def __init__(self, *args, **kwargs):
        Rst2BashError.__init__(self, *args, **kwargs)


class InvalidCodeBlockError(Rst2BashError):
    """Error describing unspported code blocks for rst2bash."""

    pass


class InvalidOperatorError(Rst2BashError):
    """Error describing bash/db operators which are not supported."""

    pass
