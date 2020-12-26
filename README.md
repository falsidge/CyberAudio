# CyberAudio
Extracts opuspak files and opus wem files from Cyberpunk 2077.
Requires [python](https://www.python.org/) 

# Usage
```extract_opuspak.py -h```
```extract_opuspak.py base/sound/soundbanks/sfx_container_0.opuspak```
```extract_opuspak.py base/sound/soundbanks```
```extract_opuspak.py base/sound/soundbanks -o out```
```extract_opuspak.py base/sound/soundbanks -o out --single```
```extract_opuspak.py base/sound/soundbanks -o out --single --pattern {file_name}_{total_index}_{index}.wem```
```extract_opuspak.py base/sound/soundbanks -o out --single --opus```
