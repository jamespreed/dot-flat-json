from json.decoder import scanstring
from json import JSONDecodeError
import re


FLAGS = re.VERBOSE | re.MULTILINE | re.DOTALL
NUMBER_RE = re.compile(r'(-?(?:0|[1-9]\d*))(\.\d+)?([eE][-+]?\d+)?', FLAGS)
STRINGCHUNK = re.compile(r'(.*?)(["\\\x00-\x1f])', FLAGS)
WHITESPACE = re.compile(r'[ \t\n\r]*', FLAGS)
WHITESPACE_STR = ' \t\n\r'
CONSTANTS = {
    '-Infinity': float('-inf'),
    'Infinity': float('inf'),
    'NaN': float('nan'),
    'true': True,
    'false': False,
    'null': None,
}
BACKSLASH = {
    '"': '"', '\\': '\\', '/': '/',
    'b': '\b', 'f': '\f', 'n': '\n', 'r': '\r', 't': '\t',
}


class FlatJSONParser:
    _match_number = NUMBER_RE.match
    _parse_constant = CONSTANTS.__getitem__
    _ws_match = WHITESPACE.match
    _ws_str = WHITESPACE_STR

    def __init__(
        self,
        key_sep: str='.',
        encase_dict_key: str|tuple='<>',
        encase_list_ix: str|tuple='[]',
        ) -> None:
        """
        args:
            key_sep: the string used to separate keys
            encase_dict_key: pair of strings that surround a dictionary key
                when the key contains the `key_sep` string.  I.e. the JSON
                key "hello.world" becomes <hello.world> with the defaults.
            encase_list_ix: pair of strings that surround a list index in
                joined key chain.  Default shows indexes as `.[0]`
        """
        if len(encase_dict_key) != 2:
            raise ValueError('`encase_dict_key` must be of length 2.')
        if encase_list_ix and len(encase_list_ix) != 2:
            raise ValueError('`encase_list_ix` must be of length 2.')
        self.key_sep = key_sep
        self.encase_dict_key = tuple(map(str, encase_dict_key))
        self.encase_list_ix = tuple(map(str, encase_list_ix))
        self._ancestor_keys = []
        self._level = 0

    @property
    def _parent_key(self) -> str:
        return self.key_sep.join(self._ancestor_keys)

    def _encase_key_if_has_sep(self, key: str) -> str:
        """
        Surrounds the dictionary key in the key chain if it contains
        the seperator string.

        args:
            key: dictionary key within the chain of keys.
        returns:
            str
        """
        if self.key_sep in key:
            return f'{self.encase_dict_key[0]}{key}{self.encase_dict_key[1]}'
        return key

    def _encase_ix(self, ix: int) -> str:
        """
        Surrounds the list index in the key chain.

        args:
            ix: list index within the chain of keys.
        returns:
            str
        """
        if self.encase_list_ix:
            return f'{self.encase_list_ix[0]}{ix}{self.encase_list_ix[1]}'
        return f'{ix}'

    def _parse_next(self, string: str, idx: int) -> tuple:
        """
        Parses the next encountered item in the JSON string.

        args:
            string: an entire JSON string.
            idx: the index in the JSON string to begin parsing.
        returns:
            tuple: (list of tuples of chained-keys and value,
                    end index of the parsed object)
        """
        idx = self._skip_whitespace(string, idx)
        try:
            nextchar = string[idx]
        except IndexError:
            raise StopIteration(idx) from None

        if nextchar == '"':
            return scanstring(string, idx + 1)
        elif nextchar == '{':
            return self._parse_object(string, idx + 1)
        elif nextchar == '[':
            return self._parse_array(string, idx + 1)
        elif (num_match := self._match_number(string, idx)):
            return self._parse_numeric(num_match)
        elif (const_idx_tup := self._parse_constants(nextchar, string, idx)):
            return const_idx_tup
        else:
            raise StopIteration(idx)

    def _parse_constants(self, nextchar: str, string: str, idx: int) -> tuple:
        if nextchar == 'n' and string[idx:idx + 4] == 'null':
            return None, idx + 4
        elif nextchar == 't' and string[idx:idx + 4] == 'true':
            return True, idx + 4
        elif nextchar == 'f' and string[idx:idx + 5] == 'false':
            return False, idx + 5
        elif nextchar == 'N' and string[idx:idx + 3] == 'NaN':
            return self._parse_constant('NaN'), idx + 3
        elif nextchar == 'I' and string[idx:idx + 8] == 'Infinity':
            return self._parse_constant('Infinity'), idx + 8
        elif nextchar == '-' and string[idx:idx + 9] == '-Infinity':
            return self._parse_constant('-Infinity'), idx + 9
        return tuple()

    @staticmethod
    def _parse_numeric(num_match: re.Match) -> int|float:
        """
        Returns the numeric value of the matched string.
        """
        integer, frac, exp = num_match.groups()
        if frac or exp:
            res = float(integer + (frac or '') + (exp or ''))
        else:
            res = int(integer)
        return res, num_match.end()

    def _skip_whitespace(self, string: str, idx: int) -> int:
        """
        Skip whitespace characters.  Returns the index of the end of white
        space.
        """
        new_idx = self._ws_match(string, idx).end()
        return new_idx

    def _parse_array(
        self,
        string: str,
        idx: int,
        ) -> tuple[list[tuple[str, int|float|str|bool|None]], int]:
        """
        Sub-parser for when an opening square bracket `[` is encounter
        indicating the start of a JSON array.

        args:
            string: an entire JSON string.
            idx: the index in the JSON string to begin parsing.
        returns:
            tuple: (list of tuples of chained-keys and value,
                    end index of the parsed array)
        """
        pairs = []

        # move cursor to next non-whitespace
        idx = self._skip_whitespace(string, idx)
        nextchar = string[idx:idx + 1]

        # trivial empty object: []
        if nextchar == ']':
            return [(self._parent_key, [])], idx

        array_key = -1
        while True:
            array_key += 1
            self._ancestor_keys.append(self._encase_ix(array_key))
            idx = self._skip_whitespace(string, idx)
            nextchar = string[idx:idx + 1]

            # if nextchar in '{':
            #     self._ancestor_keys.pop()

            try:
                value_or_values, idx = self._parse_next(string, idx)
            except StopIteration as err:
                raise JSONDecodeError("Expecting value", string, err.value) from None

            if nextchar in '[{':
                pairs.extend(value_or_values)
            else:
                pairs.append((self._parent_key, value_or_values))

            self._ancestor_keys.pop()
            idx = self._skip_whitespace(string, idx)
            nextchar = string[idx:idx + 1]

            ### END OF ARRAY
            ###########################
            if nextchar == ']':
                break

            ### CONTINUES TO NEXT VALUE
            ###########################
            elif nextchar != ',':
                raise JSONDecodeError("Expecting ',' delimiter", str, idx)

            idx = self._skip_whitespace(string, idx + 1)
        return pairs, idx + 1

    def _parse_object(
        self,
        string: str,
        idx: int,
        ) -> tuple[list[tuple[str, int|float|str|bool|None]], int]:
        """
        Sub-parser for when an opening curly bracket `{` is encounter,
        indicating that start of a JSON object.

        args:
            string: an entire JSON string.
            idx: the index in the JSON string to begin parsing.
        returns:
            tuple: (list of tuples of chained-keys and value,
                    end index of the parsed object)
        """
        pairs = []

        # move cursor to next non-whitespace
        idx = self._skip_whitespace(string, idx)
        nextchar = string[idx:idx + 1]

        # trivial empty object: {}
        if nextchar == '}':
            return [(self._parent_key, {})], idx

        if nextchar != '"':
            raise JSONDecodeError(
                "Expecting property name enclosed in double quotes", string, idx
            )

        idx += 1
        while True:
            key, idx = scanstring(string, idx)
            self._ancestor_keys.append(self._encase_key_if_has_sep(key))
            idx = self._skip_whitespace(string, idx)

            if string[idx:idx + 1] != ':':
                raise JSONDecodeError("Expecting ':' delimiter", string, idx)

            # move over the ':'
            idx = self._skip_whitespace(string, idx + 1)
            nextchar = string[idx:idx + 1]

            try:
                value_or_values, idx = self._parse_next(string, idx)
            except StopIteration as err:
                raise JSONDecodeError("Expecting value", string, err.value)

            if nextchar in '[{':
                pairs.extend(value_or_values)
            else:
                pairs.append((self._parent_key, value_or_values))

            idx = self._skip_whitespace(string, idx)
            nextchar = string[idx:idx + 1]

            ### END OF OBJECT
            ###########################
            if nextchar == '}':
                self._ancestor_keys.pop()
                break

            ### CONTINUE TO NEXT PAIR
            ###########################
            elif nextchar != ',':
                raise JSONDecodeError("Expecting ',' delimiter", string, idx)

            idx = self._skip_whitespace(string, idx + 1)
            nextchar = string[idx:idx + 1]

            if nextchar != '"':
                raise JSONDecodeError(
                    "Expecting property name enclosed in double quotes", string, idx
                )

            idx += 1
            self._ancestor_keys.pop()
        return pairs, idx + 1

    def parse(self, json_string: str) -> dict[str, int|float|str|bool|None]:
        """
        Parses the JSON string to a flat dictionary with keys chained together
        from the nested objects and arrays of the JSON string.

        args:
            json_string: a JSON formatted string to parse
        returns:
            dict
        """
        self._ancestor_keys.clear()
        out, _ = self._parse_next(json_string, 0)
        return dict(out)

if __name__ == '__main__':
    import pprint
    jfp = FlatJSONParser()
    pprint.pp(jfp.parse(
    """
    {
        "object": {
            "array": ["b", "c", 10, {"hello": "world"} ]
        }
    }
    """
    ))