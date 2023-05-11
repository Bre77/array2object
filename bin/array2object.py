#!/usr/bin/env python

import sys
import os
import json

sys.path.append(os.path.join(os.path.dirname(__file__), "..", 'lib'))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

@Configuration()
class array2objectCommand(StreamingCommand):
    field=Option(
        doc='''
        **Syntax:** **field=***<field>*
        **Description:** The field containing the JSON to process. Defaults to _raw.''',
        require=False, default="_raw", validate=validators.Fieldname()
    )
    path=Option(
        doc='''
        **Syntax:** **path=***<string>*
        **Description:** Path in dot notation to the array.''',
        require=True
    )
    key=Option(
        doc='''
        **Syntax:** **key=***<string>*
        **Description:** Field to use as the key. Must be present or else array item will be skipped.''',
        require=True
    )
    value=Option(
        doc='''
        **Syntax:** **value=***<string>*
        **Description:** Optional child path to use as the value(s).''',
        require=False
    )

    def dotpath(self,path,target):
        for step in path.split("."):
            if isinstance(target,dict):
                target = target[step]
            elif isinstance(target,list) and step.isnumeric():
                target = target[int(step)]
            else:
                raise ValueError
        return target

    def loop_dict(self,event,key,child,ignore):
        for index in child:
            nextkey = f'{key}.{index}'
            if nextkey == ignore:
                continue
            self.recursive_field(event,nextkey,child[index],ignore)

    def loop_list(self,event,key,child,ignore):
        for value in child:
            self.recursive_field(event,f'{key}{{}}',value,ignore)

    def recursive_field(self,event,key,value,ignore):
        if isinstance(value,dict):
            # Traverse object
            self.loop_dict(event,key,value,ignore)
        elif isinstance(value,list):
            # Traverse array
            self.loop_list(event,key,value,ignore)
        elif key not in event:
            # Add field for the first time
            self.add_field(event,key,value)
        elif event[key] == None:
            # Replace null value
            event[key] = value
        elif isinstance(event[key],list):
            # Append to multivalue
            event[key].append(value)
        else:
            # Make multivalue
            event[key] = [event[key],value]

    def stream(self, events):
        for event in events:
            # Get JSON
            try:
                data = json.loads(event[self.field])
            except (ValueError,KeyError) as e:
                yield event
                continue

            # Get data at provided path
            try:
                data = self.dotpath(self.path,data)
            except (ValueError,KeyError,IndexError):
                yield event
                continue
        
            # Confirm target is an array
            if not isinstance(data,list):
                yield event
                continue

            # Iterate the array
            for item in data:
                # Get keys value and prepend it to path
                try:
                    key_value = self.dotpath(self.key,item)
                except (ValueError,KeyError,IndexError) as e:
                    continue

                if(isinstance(key_value,dict) or isinstance(key_value,list)):
                    continue
                
                # Create this items starting key
                key = f'{self.path}.{key_value}'

                if self.value:
                    # Get children from provided path
                    try:
                        item = self.dotpath(self.value,item)
                    except (ValueError,KeyError,IndexError) as e:
                        continue
                    #Create all children
                    self.recursive_field(event,key,item,None)
                else:
                    #Create all children but exclude the key
                    self.loop_dict(event,key,item,f'{key}.{self.key}')
            yield event

dispatch(array2objectCommand, sys.argv, sys.stdin, sys.stdout, __name__)
