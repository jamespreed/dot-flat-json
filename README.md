# dot-flat-json
Parses JSON data directly to a flat dictionary with dotted keys without parsing to Python objects first.  


{"x.y.z": 10}

## Example
Given a JSON object such as:

```json
{
  "objectKey": {
    "arrayKey": ["b", "c", 10, {"hello": "world"} ]
  },
  "someOtherKey": {
    "x": 10,
    "y": 12,
    "z": -2.3,
    "alt": null
  }
}
```

It will be parsed to following structure in Python:
```python
{
    'objectKey.arrayKey.[0]': 'b',
    'objectKey.arrayKey.[1]': 'c',
    'objectKey.arrayKey.[2]': 10,
    'objectKey.arrayKey.[3].hello': 'world',
    'someOtherKey.x': 10,
    'someOtherKey.y': 12,
    'someOtherKey.z': -2.3,
    'someOtherKey.alt': None
}
```

## Usage and Options
The `FlatJSONParser` class handles parsing the JSON string and formatting the chained keys.  

```python
>>> json_str = """{"hello": {"world": { "this is a test": "PING!" } } } """
>>> fjp = FlatJSONParser()
>>> fjp.parse(json_str)
{'hello.world.this is a test': 'PING!'}
```

### Key separator
The seperator between elements in the key chains can be changed using the `key_sep` argument.
```python
>>> fjp = FlatJSONParser(key_sep='|')
>>> fjp.parse(json_str)
{'hello|world|this is a test': 'PING!'}
```

### Dict keys containing `key_sep`
If a key in the key chain contains the `key_sep` string, it will be encased in the `encase_dict_key` pair of strings. The default is `<>`
```python
>>> json_str = """{
  "hello": {"world": { "this.is.a.test": "PING!" } },
  "good.night": "moon."
}
"""
>>> fjp = FlatJSONParser()
>>> fjp.parse(json_str)
{'hello.world.<this.is.a.test>': 'PING!',
 '<good.night>': 'moon.'}
```

This argument can be passed either as a string of length 2, or as a tuple of strings. 
```python
>>> json_str = """{
  "hello": {"world": { "this.is.a.test": "PING!" } },
  "good.night": "moon."
}
"""
>>> fjp = FlatJSONParser(encase_dict_key=('<|', '|>'))
>>> fjp.parse(json_str)
{ 'hello.world.<|this.is.a.test|>': 'PING!',
 '<|good.night|>': 'moon.' }
```

### Array index encasement
The index of each element in a JSON array is added to the key chain.  The default is to surround the index with the `encase_list_ix` string pair, the default is `'[]'`.  
Passing an empty string or `None` will remove the encasement.
```python
>>> json_str = """{ "goodnight": ["moon", "room", "cow"] } """
>>> fjp = FlatJSONParser(encase_dict_key=('<|', '|>'))
>>> fjp.parse(json_str)
{'goodnight.[0]': 'moon',
 'goodnight.[1]': 'room',
 'goodnight.[2]': 'cow'}
```

### Arrays of objects
Arrays of objects are chained as you would expect, with the keys from the JSON ojects chaining against the array index.
```python
>>> json_str = """{ "goodnight": [{"moon": "zzz..."}, {"room": "shhhh...."}, {"cow": "moooo?"}] } """
>>> fjp = FlatJSONParser(encase_dict_key=('<|', '|>'))
>>> fjp.parse(json_str)
{'goodnight.[0].moon': 'zzz...',
 'goodnight.[1].room': 'shhhh....',
 'goodnight.[2].cow': 'moooo?'}
```
