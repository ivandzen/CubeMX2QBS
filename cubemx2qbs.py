#This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

import xml.etree.ElementTree as ET
import json
import argparse
import os.path
import re

libs_ld_contents = """GROUP(
 libgcc.a
 libg.a
 libc.a
 libm.a
 libstdc++.a
 libnosys.a
)
"""

STM32F0_Compiler_Flags = [ "-mthumb", "-mcpu=cortex-m0" ]
STM32F1_Compiler_Flags = [ "-mthumb", "-mcpu=cortex-m3" ]    
STM32F2_Compiler_Flags = [ "-mthumb", "-mcpu=cortex-m3" ]
STM32F4_Compiler_Flags = [ "-mthumb", "-mcpu=cortex-m4", "-mfloat-abi=hard", "-mfpu=fpv4-sp-d16" ]
STM32F7_Compiler_Flags = [ "-mthumb", "-mcpu=cortex-m7", "-mfloat-abi=hard", "-mfpu=fpv5-sp-d16" ]

Linker_Flags = [ "-Xlinker",
        	 "--gc-sections",
        	 "-lgcc",
        	 "-lc",
        	 "-specs=nosys.specs",
        	 "-lnosys" ]

project_name = ""
processor_name = ""
includepaths = []

################################################################################

def qbsWriteArray(arr, str_prefix = "") :
	result = "[ \n"
	for item in arr :
		result += str_prefix
		if isinstance(item, str) :
			result += "\"" + str(item) + "\""
		else :
			result += str(item)
		result += ",\n"
	result = result[:-2]
	result += "\n" + str_prefix + "]\n"
	return result

def qbsWriteItem(name, elements, str_prefix = "") :
	result = str_prefix + name + " {\n"
	for key, value in elements.iteritems() :
		result += str_prefix + "    " + key + ": "
		if isinstance(value, list) :
			result += qbsWriteArray(value, str_prefix + "        ")
		elif isinstance(value, str) :
			result += "\"" + value + "\""
		else :
			result += str(value)
	result += "\n" + str_prefix + "}"
	return result


################################################################################

def parsePackage(pack) :
	global project_name
	defineProcessorName = ''
	tmp = ""
	for child in pack :
		if child.tag == 'name' :
			project_name = child.text
		elif child.tag == 'requirements' :
			tmp += parseRequirements(child)
		elif child.tag == 'generators' :
			tmp += parseGenerators(child)
		elif child.tag == 'conditions' :
			tmp += parseConditions(child)
		elif child.tag == 'components' :
			tmp += parseComponents(child)
			# find the lines like:
			# <file category="sourceAsm" condition="GCC Toolchain"
			# name="Drivers\CMSIS\Device\ST\STM32F1xx\Source\Templates\gcc\startup_stm32f103xb.s"/>
			# and extract the stm32f103xb from them
			for component in child :
				if ('Cgroup' in component.attrib and component.attrib['Cgroup'] == 'Startup') :
					for files in component.findall('files') :
						for f in files.findall('file') :
							if ('condition' in f.attrib and f.attrib['condition'] == 'GCC Toolchain') :
								result = re.match( r'.*startup_(.*)\.s', f.attrib['name'], re.M|re.I)
								print result.group(1).upper()
								defineProcessorName = result.group(1).upper().replace('X', 'x')

	result = "import qbs\n\n"
	result += "Product {\n"
	result += "    Depends { name : \"cpp\" }\n"
	result += "    type: \"application\"\n"
	result += "    consoleApplication: true\n"
	result += "    cpp.positionIndependentCode: false\n"
	result += "    name: \"" + project_name + "\"\n"
	result += "    cpp.includePaths : " + qbsWriteArray(includepaths, "        ") + "\n"
	result += "    cpp.linkerScripts : [ \"" + processor_name + "_FLASH.ld\", \"LIBS.ld\"" + " ]\n"

	if "STM32F0" in processor_name :
		result += "    cpp.commonCompilerFlags: " + qbsWriteArray(STM32F0_Compiler_Flags, "        ")
		result += "    cpp.linkerFlags: " + qbsWriteArray(STM32F0_Compiler_Flags + Linker_Flags, "        ")
	elif "STM32F1" in processor_name :
		result += "    cpp.commonCompilerFlags: " + qbsWriteArray(STM32F1_Compiler_Flags, "        ")
		result += "    cpp.linkerFlags: " + qbsWriteArray(STM32F1_Compiler_Flags + Linker_Flags, "        ")
	elif "STM32F2" in processor_name :
		result += "    cpp.commonCompilerFlags: " + qbsWriteArray(STM32F2_Compiler_Flags, "        ")
		result += "    cpp.linkerFlags: " + qbsWriteArray(STM32F2_Compiler_Flags + Linker_Flags, "        ")
	elif "STM32F4" in processor_name :
		result += "    cpp.commonCompilerFlags: " + qbsWriteArray(STM32F4_Compiler_Flags, "        ")
		result += "    cpp.linkerFlags: " + qbsWriteArray(STM32F4_Compiler_Flags + Linker_Flags, "        ")
	elif "STM32F7" in processor_name :
		result += "    cpp.commonCompilerFlags: " + qbsWriteArray(STM32F7_Compiler_Flags, "        ")
		result += "    cpp.linkerFlags: " + qbsWriteArray(STM32F7_Compiler_Flags + Linker_Flags, "        ")


	result += "    cpp.defines: [ \"" + defineProcessorName + "\" ]\n"

	result += tmp
	result += "}"
	return result

################################################################################

def parseRequirements(reqs) :
	result = ""
	for child in reqs :
		if child.tag == 'languages' :
			result += parseLanguages(child)
	result += "\n\n"
	return result

def parseLanguages(langs) :
	result = ""
	for child in langs :
		if child.tag == 'language' :
			if child.attrib["name"] == "C" :
				result += "    cpp.cLanguageVersion: \"c" + child.attrib['version'] + "\"\n"
			elif child.attrib["name"] == "C++" :
			 	result += "    cpp.cxxLanguageVersion: \"c++" + child.attrib['version'] + "\"\n"
	return result

def parseGenerators(generators) :
	result = ""
	for child in generators :
		if child.tag == 'generator' :
			result += parseGenerator(child)
	return result

def parseGenerator(gen) :
	group = {}
	group['name'] = gen.attrib['id']
	for child in gen :
		if child.tag == 'select' :
			parseProcessorName(child)
		elif child.tag == 'project_files' :
			group['files'] = parseFiles(child)
	return qbsWriteItem("Group", group, "    ") + "\n\n"

def parseProcessorName(select) :
	global processor_name
	processor_name = select.attrib['Dname']

def parseFiles(files) :
	result = []
	for child in files :
		if child.tag == 'file' :
			if child.attrib.has_key('condition') and child.attrib['condition'] != 'GCC Toolchain' :
				continue
			cur_file = child.attrib['name'].replace('\\', '/')
			dir_name = os.path.dirname(cur_file)
			if cur_file[-2:] == ".h" and includepaths.count(dir_name) == 0 :
				includepaths.append(dir_name)
			result.append(cur_file)
	return result

def parseConditions(cond) :
	return ""

def parseComponents(comp) :
	result = ""
	for child in comp :
		if child.tag == 'component' :
			result += parseComponent(child)
	return result

def parseComponent(comp) :
	group = {}
	group_name = ""
	if comp.attrib.has_key('Cclass') : group_name += comp.attrib['Cclass']
	if comp.attrib.has_key('Cgroup') : group_name += "." + comp.attrib['Cgroup']
	if comp.attrib.has_key('Csub') : group_name += "." + comp.attrib['Csub']
	group['name'] = group_name
	for child in comp :
		if child.tag == 'files' :
			group['files'] = parseFiles(child)
	return qbsWriteItem("Group", group, "    ") + "\n\n"

################################################################################

parser = argparse.ArgumentParser("Convert GPDSC project files to Qt Build Suite project files")
parser.add_argument('filename', action = 'store')

args = parser.parse_args()

input_filename = vars(args)['filename']

tree = ET.parse(input_filename)

root = tree.getroot()

if root.tag != 'package' :
	print("Invalid GPDSC file format : '" + 'package' + "' element expected")
	exit(1)

outfile_contents = parsePackage(root)

output_filename = project_name + ".qbs"

output_file = open(output_filename, "w")

output_file.write(outfile_contents)

output_file.close()

libs_ld_file = open("LIBS.ld", "w")
libs_ld_file.write(libs_ld_contents)
libs_ld_file.close()
