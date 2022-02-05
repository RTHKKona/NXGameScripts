import json
import glob
import os
import sys
import struct

def GetFileSize(file):
	pos = file.tell()
	file.seek(0, 2)
	size = file.tell()
	file.seek(pos)
	return size

def readString(myfile):
	chars = []
	while True:
		c = myfile.read(1)
		if c == b'\x00':
			return str(b"".join(chars).decode("UTF-8"))
		chars.append(c)

def readStringDialog(myfile):
	chars = []
	while True:
		c = myfile.read(1)
		test = int.from_bytes(c, byteorder="little")
		if (0xE0 > test >= 0xC0):
			chars.append(c)
			chars.append(myfile.read(1))
		elif (0xE0 <= test <= 0xF7):
			chars.append(c)
			chars.append(myfile.read(1))
			chars.append(myfile.read(1))
		elif (test > 0xF7):
			chars.append(c)
		elif (test >= 0x20):
			chars.append(c)
		elif test < 0x20:
			myfile.seek(-1, 1)
			return str(b"".join(chars).decode("UTF-8"))

def ReadDialog(file, entry):
	entry["CONTROLS"] = []
	entry["STRINGS"] = []
	while(True):
		entry["CONTROLS"].append(int.from_bytes(file.read(1), byteorder="little"))
		type_check = [1, 3, 6, 7, 8, 9, 0xB, 0xC]
		if (entry["CONTROLS"][len(entry["CONTROLS"]) - 1] in type_check):
			entry["STRINGS"].append(readStringDialog(file))
			continue
		match(entry["CONTROLS"][len(entry["CONTROLS"]) - 1]):
			case 0:
				return
			
			case 2:
				pass
			
			case 0x10:
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little"))

			case 0x11:
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little"))
				entry["STRINGS"].append(readStringDialog(file))
			
			case 0x12:
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little"))
				entry["STRINGS"].append(readStringDialog(file))
			
			case 0x23:
				file.seek(-1, 1)
				entry["STRINGS"].append(readStringDialog(file))
			
			case _:
				if (entry["CONTROLS"][len(entry["CONTROLS"]) - 1] >= 0x20):
					file.seek(-1, 1)
					entry["STRINGS"].append(readStringDialog(file))
				else:
					print("UNKNOWN DIALOG COMMAND: 0x%x" % entry["CONTROLS"][len(entry["CONTROLS"]) - 1])
					print("OFFSET: 0x%x" % (file.tell() - 1))
					sys.exit()

def CalcGoto(file, entry, end):
	entry["CONTROLS"] = []
	control = int.from_bytes(file.read(1), byteorder="little")
	entry["CONTROLS"].append(control)
	passing = [2, 3, 4, 5, 6, 7, 8, 9, 0xA, 0xB, 0xC, 0xD, 0xE, 0x10, 0x12, 0x13, 0x22]
	while (control != 1):
		if (control in passing):
			control = int.from_bytes(file.read(1), byteorder="little")
			entry["CONTROLS"].append(control)
			continue
		match(control):
			case 0:
				entry["UNK"] = [int.from_bytes(file.read(4), byteorder="little")]
			
			case 0x1E:
				entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little")]

			case 0x1F:
				entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little")]

			case 0x20:
				entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little")]
			
			case 0x21:
				entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little")]
				entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little")]

			case 0x23:
				entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little")]
			
			case 0x24:
				entry["UNK"] = [int.from_bytes(file.read(4), byteorder="little")]

			case 0x25:
				entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little")]
			
			case 0x1C:
				cmd = int.from_bytes(file.read(1), byteorder="little")
				entry["INSTRUCTION"] = GenerateCommand(cmd, file, end)
			
			case _:
				print("UNKNOWN GOTO COMMAND: 0x%x" % control)
				print("OFFSET: 0x%x" % (file.tell() - 1))
				sys.exit()
			
		control = int.from_bytes(file.read(1), byteorder="little")
		entry["CONTROLS"].append(control)
		

def GenerateCommand(cmd, file, end):
	entry = {}
	entry["LABEL"] = "0x%x" % (file.tell() - 1)
	print("0x%x" % cmd)
	match(cmd):
		case 0:
			if ((end - file.tell()) < 4):
				file.seek(end)
			else:
				print("NOP DETECTED. DISASSEMBLING FAILED")
				print("OFFSET: 0x%x" % (file.tell() - 1))
				sys.exit()
		case 1:
			entry["TYPE"] = "RETURN"
		
		case 2:
			entry["TYPE"] = "0x2"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
			entry["STRINGS"] = [readString(file)]
		
		case 3:
			entry["TYPE"] = "GOTO3"
			entry["TO_LABEL"] = "0x%x" % int.from_bytes(file.read(4), byteorder="little")
		
		case 4:
			entry["TYPE"] = "0x4"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
			entry["STRINGS"] = [readString(file)]

		case 5:
			entry["TYPE"] = "GOTO5"
			CalcGoto(file, entry, end)
			entry["TO_LABEL"] = "0x%x" % int.from_bytes(file.read(4), byteorder="little")
		
		case 6:
			entry["TYPE"] = "GOTO6"
			CalcGoto(file, entry, end)
			count = int.from_bytes(file.read(1), byteorder="little")
			entry["TO_LABELS"] = []
			for i in range(0, count):
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little"))
				entry["TO_LABELS"].append("0x%x" % int.from_bytes(file.read(4), byteorder="little"))
			entry["TO_LABELS"].append("0x%x" % int.from_bytes(file.read(4), byteorder="little"))
		
		case 7:
			entry["TYPE"] = "0x7"
			entry["UNK"] = [int.from_bytes(file.read(4), byteorder="little", signed=True)]
		
		case 8:
			entry["TYPE"] = "0x8"
			CalcGoto(file, entry, end)
		
		case 0xA:
			entry["TYPE"] = "0xA"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
			CalcGoto(file, entry, end)
		
		case 0xC:
			entry["TYPE"] = "0xC"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
		
		case 0xD:
			entry["TYPE"] = "0xC"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
		
		case 0xE:
			entry["TYPE"] = "0xE"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
		
		case 0xF:
			entry["TYPE"] = "0xF"
			entry["UNK"] = [int.from_bytes(file.read(4), byteorder="little", signed=True)]
		
		case 0x10:
			entry["TYPE"] = "0x10"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
		
		case 0x11:
			entry["TYPE"] = "0x10"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))

		case 0x12:
			entry["TYPE"] = "0x12"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
			CalcGoto(file, entry, end)
		
		case 0x13:
			entry["TYPE"] = "0x13"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["STRINGS"] = [readString(file), readString(file), readString(file)]
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["STRINGS"].append(readString(file))
			entry["STRINGS"].append(readString(file))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
		
		case 0x14:
			entry["TYPE"] = "0x14"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
			entry["STRINGS"] = [readString(file)]
		
		case 0x15:
			entry["TYPE"] = "0x15"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
		
		case 0x16:
			entry["TYPE"] = "0x16"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
		
		case 0x17:
			entry["TYPE"] = "0x17"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]

		case 0x18:
			entry["TYPE"] = "0x18"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			ReadDialog(file, entry)

		case 0x19:
			entry["TYPE"] = "0x19"
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little", signed=True)
			entry["UNK"] = []
			match(entry["CONTROL"]):
				case 0:
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
				
				case 1:
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
				
				case 2:
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))

				case 5:
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
				
				case _:
					print("UNKNOWN 0x19 CONTROL: 0x%x" % entry["CONTROL"])
					print("OFFSET: 0x%x" % (file.tell - 2))
		
		case 0x1A:
			entry["TYPE"] = "0x1A"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			ReadDialog(file, entry)

		case 0x1B:
			entry["TYPE"] = "0x1B"
			
		case 0x1C:
			entry["TYPE"] = "0x1C"
		
		case 0x1D:
			entry["TYPE"] = "0x1D"
			entry["STRINGS"] = [readString(file)]
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
		
		case 0x1E:
			entry["TYPE"] = "0x1E"
			entry["STRINGS"] = [readString(file), readString(file)]

		case 0x1F:
			entry["TYPE"] = "0x1F"
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little", signed=True)
			entry["CONTROL2"] = int.from_bytes(file.read(1), byteorder="little", signed=True)
			assert(entry["CONTROL2"] < 4)
			entry["UNK"] = []
			match(entry["CONTROL"]):
				case 0:
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				
				case 1:
					entry["STRINGS"] = [readString(file)]
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				
				case 2:
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				
				case 3:
					pass
				
				case 4:
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
				
				case 5:
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				
				case 6:
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				
				case 7:
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				
				case 0xC:
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				
				case _:
					print("UNKNOWN 0x19 CONTROL: 0x%x" % entry["CONTROL"])
					print("OFFSET: 0x%x" % (file.tell() - 1))
					sys.exit()

		case 0x20:
			entry["TYPE"] = "0x20"
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little")
			assert(entry["CONTROL"] <= 2)
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			if (entry["CONTROL"] > 0):
				entry["UNK"].append(int.from_bytes(file.read(entry["CONTROL"]), byteorder="little", signed=True))
			entry["STRINGS"] = [readString(file), readString(file)]
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
		
		case 0x21:
			entry["TYPE"] = "0x21"
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little")
			entry["UNK"] = [int.from_bytes(file.read(4), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
			if (entry["CONTROL"] == 1):
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
		
		case 0x22:
			entry["TYPE"] = "0x22"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["STRINGS"] = [readString(file)]
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
		
		case 0x23:
			entry["TYPE"] = "0x23"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))

		case 0x24:
			entry["TYPE"] = "0x24"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["STRINGS"] = [readString(file), readString(file)]

		case 0x25:
			entry["TYPE"] = "0x25"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["STRINGS"] = [readString(file), readString(file)]
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])

		case 0x26:
			entry["TYPE"] = "0x26"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
			entry["STRINGS"] = [readString(file)]
		
		case 0x27:
			entry["TYPE"] = "0x27"
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little", signed=True)
			match(entry["CONTROL"]):
				case 0xA:
					entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
					entry["STRINGS"] = [readString(file)]
				case 0xC:
					entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["STRINGS"] = [readString(file)]
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
				case 0x12:
					entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				case 0x15:
					entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
					entry["STRINGS"] = [readString(file)]
				case _:
					if (entry["CONTROL"] in [0x11, 0x10, 0xF, 0xB, 0xD, 0xE]):
						entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
						entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
					elif (entry["CONTROL"] in [0x13, 0x14]):
						entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
						entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
						entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
						entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
						entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
						entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
					else:
						print("UNKNOWN 0x27 CONTROL: 0x%x" % entry["CONTROL"])
						print("OFFSET: 0x%x" % (file.tell() - 2))
						sys.exit()
					
		case 0x29:
			entry["TYPE"] = "0x29"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
		
		case 0x2A:
			entry["TYPE"] = "0x2A"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
		
		case 0x2B:
			entry["TYPE"] = "0x2B"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
		
		case 0x2C:
			entry["TYPE"] = "0x2C"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
		
		case 0x2D:
			entry["TYPE"] = "0x2D"
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little", signed=True)
			entry["UNK"] = []
			if (entry["CONTROL"] in [0, 0x10]):
				return
			match(entry["CONTROL"]):
				case 2:
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				
				case 3:
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["STRINGS"] = [readString(file)]
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))

				case 0x14:
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["STRINGS"] = [readString(file)]
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				
				case 4:
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
				
				case 5:
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				
				case 7:
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				
				case 8:
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				
				case 9:
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
				
				case 0xB:
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				
				case 0xC:
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				
				case 0xD:
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))

				case 0xE:
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				
				case 0xF:
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
				
				case 0x11:
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
				
				case 0x12:
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				
				case 0x13:
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
				
				case 0x15:
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
				
				case 0x16:
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				
				case 0x17:
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				
				case _:
					print("UNKNOWN 0x2D CONTROL BYTE: 0x%x" % entry["CONTROL"])
					print("OFFSET: 0x%x" % (file.tell() - 2))
					sys.exit()
		
		case 0x2E:
			entry["TYPE"] = "0x2E"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
		
		case 0x2F:
			entry["TYPE"] = "0x2F"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
			entry["STRINGS"] = [readString(file)]
		
		case 0x30:
			entry["TYPE"] = "0x30"
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little")
			check = [7]
			if (entry["CONTROL"] in check):
				return
			match(entry["CONTROL"]):
				case 0:
					entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
					entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))

				case 1:
					entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
				
				case 2:
					entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
				
				case 3:
					entry["UNK"] = [struct.unpack("<f", file.read(4))[0]]
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))

				case 4:
					entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
				
				case 5:
					entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				
				case 6:
					entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
				
				case _:
					print("UNKNOWN 0x30 CONTROL: 0x%x" % entry["CONTROL"])
					print("OFFSET: 0x%x" % (file.tell() - 2))
					sys.exit()

		
		case 0x31:
			entry["TYPE"] = "0x31"
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little")
			match(entry["CONTROL"]):
				case 0xFE:
					entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
					return
				case 0xFF:
					entry["UNK"] = [int.from_bytes(file.read(4), byteorder="little", signed=True)]
					entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
					return
			if (entry["CONTROL"] in [0, 0x32]):
				entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
				entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				entry["STRINGS"] = [readString(file)]

			elif (entry["CONTROL"]  in [1, 0x33]):
				entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			
			elif (entry["CONTROL"] in [0x96, 0x39, 6, 0x38, 5, 0x37, 0x34, 2]):
				entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			
			elif(entry["CONTROL"] in [0x35, 3]):
				entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			
			elif(entry["CONTROL"] == 0x3A):
				entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			
			elif(entry["CONTROL"] == 100):
				entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			
			elif(entry["CONTROL"] == 0x65):
				entry["UNK"] = [int.from_bytes(file.read(4), byteorder="little", signed=True)]
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			
			elif(entry["CONTROL"] == 0xFD):
				entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]


		case 0x32:
			entry["TYPE"] = "0x32"
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little")
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			match(entry["CONTROL"]):
				case 1:
					entry["STRINGS"] = [readString(file), readString(file)]
				
				case 2:
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
				
				case 3:
					entry["STRINGS"] = [readString(file), readString(file), readString(file), readString(file)]
				
				case 4:
					entry["STRINGS"] = [readString(file)]
				
				case 0xA:
					pass
				
				case 0xB:
					pass
				
				case _:
					print("UNKNOWN 0x32 CONTROL: 0x%x" % entry["CONTROL"])
					print("OFFSET: 0x%x" % (file.tell() - 2))
					sys.exit()
		
		case 0x33:
			entry["TYPE"] = "0x33"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
		
		case 0x34:
			entry["TYPE"] = "0x34"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
		
		case 0x35:
			entry["TYPE"] = "0x35"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			
		case 0x36:
			entry["TYPE"] = "0x36"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["CONTROL"] = int.from_bytes(file.read(2), byteorder="little", signed=True)
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			if (-0x1ff < entry["CONTROL"] < -0x1fc):
				entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))

		case 0x37:
			entry["TYPE"] = "0x37"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
		
		case 0x38:
			entry["TYPE"] = "0x38"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
		
		case 0x39:
			entry["TYPE"] = "0x39"
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little")
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			check = [0xC, 0x5, 0x69, 0xA, 0xB, 0xFF, 0xFE]
			if (entry["CONTROL"] not in check):
				entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
		
		case 0x3A:
			entry["TYPE"] = "0x3A"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
		
		case 0x3B:
			entry["TYPE"] = "0x3B"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
		
		case 0x3C:
			entry["TYPE"] = "0x3C"
			entry["CONTROLS"] = [int.from_bytes(file.read(2), byteorder="little")]
			entry["CONTROLS"].append(int.from_bytes(file.read(2), byteorder="little"))
			entry["CONTROLS"].append(int.from_bytes(file.read(2), byteorder="little"))
			flag1 = False
			flag2 = False

			if ((entry["CONTROLS"][0] >= 0x10) and(entry["CONTROLS"][0] != 0xFFFD)):
				flag1 = True
			if ((entry["CONTROLS"][1] >= 0x10) and(entry["CONTROLS"][1] != 0xFFFD)):
				flag2 = True

			if ((flag1 == False) or (flag2 == False) or (flag1 == flag2)):
				if (entry["CONTROLS"][1] == 0xFFFF):
					entry["UNK"] = [int.from_bytes(file.read(4), byteorder="little", signed=True)]
					entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
		
		case 0x3D:
			entry["TYPE"] = "0x3D"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
			entry["STRINGS"] = [readString(file)]
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))

		case 0x3E:
			entry["TYPE"] = "0x3E"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))

		case 0x3F:
			entry["TYPE"] = "0x3F"
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little", signed=True)
			type1 = [9, 10, 11, 1, 6, 5, 4, 0, 8]
			entry["UNK"] = []
			if (entry["CONTROL"] in type1):
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			if (entry["CONTROL"] == 8):
				entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
		
		case 0x41:
			entry["TYPE"] = "0x41"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))

		case 0x42:
			entry["TYPE"] = "0x42"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
		
		case 0x43:
			entry["TYPE"] = "0x43"
			entry["UNK"] = [int.from_bytes(file.read(4), byteorder="little", signed=True)]
		
		case 0x44:
			entry["TYPE"] = "0x44"
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little")
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			match(entry["CONTROL"]):
				case 0:
					entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				
				case 1:
					pass
				
				case 2:
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
				
				case 3:
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
				
				case 4:
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				
				case 5:
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				
				case _:
					print("UNKNOWN 0x44 CONTROL: 0x%x" % entry["CONTROL"])
					print("OFFSET: 0x%x" % (file.tell() - 2))
					sys.exit()
		
		case 0x45:
			entry["TYPE"] = "0x45"
			entry["STRINGS"] = [readString(file), readString(file)]
		
		case 0x46:
			entry["TYPE"] = "0x46"
			entry["UNK"] = [int.from_bytes(file.read(4), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))

		case 0x48:
			entry["TYPE"] = "0x48"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]

		case 0x49:
			entry["TYPE"] = "0x49"
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little")
			entry["UNK"] = []
			if (entry["CONTROL"] in [0xE, 0x10, 0x11, 0x12, 0x16, 0x20]):
				return
			first_type = [10, 4, 3, 2, 1, 0]
			if (entry["CONTROL"] in first_type):
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				return
			match(entry["CONTROL"]):
				case 0xD:
					entry["STRINGS"] = [readString(file), readString(file)]
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				
				case 0x14:
					entry["STRINGS"] = [readString(file), readString(file)]
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				
				case 0x15:
					entry["STRINGS"] = [readString(file)]
				
				case 0x17:
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))

				case 0x18:
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
				
				case 0x19:
					entry["STRINGS"] = [readString(file), readString(file)]
				
				case 0x1C:
					entry["STRINGS"] = [readString(file)]
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				
				case 0x21:
					entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				
				case 0x23:
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))

				case 0x24:
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				
				case 0x26:
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
					entry["STRINGS"] = [readString(file)]

				case 0x28:
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				
				case 0x29:
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				
				case _:
					print("UNKNOWN 0x49 CONTROL: 0x%x" % entry["CONTROL"])
					print("OFFSET: 0x%x" % (file.tell() - 2))
					sys.exit()

		case 0x4A:
			entry["TYPE"] = "0x4A"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
			entry["STRINGS"] = [readString(file)]
		
		case 0x4B:
			entry["TYPE"] = "0x4B"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
		
		case 0x4C:
			entry["TYPE"] = "0x4C"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
		
		case 0x4D:
			entry["TYPE"] = "0x4D"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
		
		case 0x4F:
			entry["TYPE"] = "0x4F"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["STRINGS"] = [readString(file)]
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
		
		case 0x51:
			entry["TYPE"] = "0x51"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
			entry["STRINGS"] = [readString(file)]
		
		case 0x52:
			entry["TYPE"] = "0x52"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["STRINGS"] = [readString(file)]
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
		
		case 0x53:
			entry["TYPE"] = "0x53"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
		
		case 0x55:
			entry["TYPE"] = "0x55"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
			entry["STRINGS"] = [readString(file)]
		
		case 0x56:
			entry["TYPE"] = "0x56"
			entry["STRINGS"] = [readString(file)]
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
		
		case 0x57:
			entry["TYPE"] = "0x57"
		
		case 0x58:
			entry["TYPE"] = "0x58"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
		
		case 0x59:
			entry["TYPE"] = "0x59"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
		
		case 0x5A:
			entry["TYPE"] = "0x5A"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
			entry["STRINGS"] = [readString(file)]
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
		
		case 0x5B:
			entry["TYPE"] = "0x5B"
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little", signed=True)
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			if (entry["CONTROL"] in [0, 1, 4]):
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
		
		case 0x5C:
			entry["TYPE"] = "0x5C"
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little", signed=True)
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			if (entry["CONTROL"] in [0, 1]):
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
		
		case 0x5D:
			entry["TYPE"] = "0x5D"
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little", signed=True)
			entry["STRINGS"] = [readString(file)]
			match(entry["CONTROL"]):
				case 0:
					entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
				case 1:
					entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
				case 2:
					entry["UNK"] = [struct.unpack("<f", file.read(4))[0]]
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
				case 3:
					entry["UNK"] = [struct.unpack("<f", file.read(4))[0]]
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
				case 4:
					entry["UNK"] = [struct.unpack("<f", file.read(4))[0]]
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
				
				case 5:
					pass

				case 6:
					pass
				case 7:
					entry["UNK"] = [int.from_bytes(file.read(4), byteorder="little", signed=True)]
					entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
				case 8:
					entry["UNK"] = [int.from_bytes(file.read(4), byteorder="little", signed=True)]
					entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
				case _:
					print("UNKNOWN 0x5D CONTROL: 0x%x" % entry["CONTROL"])
					print("OFFSET: 0x%x" % (file.tell() - 2))
					sys.exit()
		
		case 0x5E:
			entry["TYPE"] = "0x5E"
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little", signed=True)
			match(entry["CONTROL"]):
				case 0:
					entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				case 6:
					entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				case 0xA:
					entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
				case _:
					if (entry["CONTROL"] in [0xB, 9, 7, 8, 4, 1]):
						entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
					elif (entry["CONTROL"] in [5, 3, 2]):
						entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
						entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
						entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					elif (entry["CONTROL"] in [0xD, 0xC]):
						entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
						entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					else:
						print("UNKNOWN 0x5E CONTROL: 0x%x" % entry["CONTROL"])
						print("OFFSET: 0x%x" % (file.tell() - 2))
						sys.exit()
		
		case 0x5F:
			entry["TYPE"] = "0x5F"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little", signed=True)
			match(entry["CONTROL"]):
				case 0:
					entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				
				case 1:
					pass

				case 2:
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
				
				case 3:
					entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				
				case _:
					print("UNKNOWN 0x5F CONTROL: 0x%x" % entry["CONTROL"])
					print("OFFSET: 0x%x" % (file.tell() - 2))
					sys.exit()
		
		case 0x60:
			entry["TYPE"] = "0x60"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
		
		case 0x61:
			entry["TYPE"] = "0x61"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
		
		case 0x62:
			entry["TYPE"] = "0x62"
			entry["STRINGS"] = [readString(file)]
			entry["UNK"] = [int.from_bytes(file.read(4), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
		
		case 0x63:
			entry["TYPE"] = "0x63"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))

		case 0x64:
			entry["TYPE"] = "0x64"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
		
		case 0x65:
			entry["TYPE"] = "0x65"
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little")
			match(entry["CONTROL"]):
				case 6:
					entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
				case 2:
					entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))	
				case 8:
					entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				case _:
					if (entry["CONTROL"] in [5, 3, 0]):
						entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
						entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
						entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
					elif (entry["CONTROL"] in [9, 7, 4, 1]):
						entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
						entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
					else:
						print("UNKNOWN 0x65 CONTROL: 0x%x" % entry["CONTROL"])
						print("OFFSET: 0x%x" % (file.tell() - 2))
						sys.exit()
		case 0x66:
			entry["TYPE"] = "0x66"
			entry["UNK"] = [struct.unpack("<f", file.read(4))[0]]
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
		
		case 0x67:
			entry["TYPE"] = "0x67"
			entry["CONTROLS"] = [int.from_bytes(file.read(2), byteorder="little")]
			entry["CONTROLS"].append(int.from_bytes(file.read(1), byteorder="little"))
			entry["UNK"] = []
			if (entry["CONTROLS"][1] in [2, 1]):
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			elif (entry["CONTROLS"][1] in [3, 4]):
				entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
			
			if ((entry["CONTROLS"][0] <= 0x96) and (entry["CONTROLS"][1] == 6)):
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
		
		case 0x68:
			entry["TYPE"] = "0x68"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little", signed=True)
			match(entry["CONTROL"]):
				case 1:
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				case 0:
					entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
				case _:
					print("UNKNOWN 0x68 CONTROL: 0x%x" % entry["CONTROL"])
					print("OFFSET: 0x%x" % (file.tell() - 2))
					sys.exit()

		case 0x69:
			entry["TYPE"] = "0x69"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little", signed=True)
			match(entry["CONTROL"]):
				case 0:
					entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				
				case 2:
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["STRINGS"] = [readString(file)]
				
				case 3:
					entry["STRINGS"] = [readString(file)]
					entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					entry["STRINGS"].append(readString(file))
				
				case 5:
					entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				
				case _:
					print("UNKNOWN 0x69 CONTROL: 0x%x" % entry["CONTROL"])
					print("OFFSET: 0x%x" % (file.tell() - 2 ))
					sys.exit()

		case 0x6A:
			entry["TYPE"] = "0x6A"
			entry["CONTROLS"] = [int.from_bytes(file.read(1), byteorder="little")]
			entry["CONTROLS"].append(int.from_bytes(file.read(1), byteorder="little"))
			if (entry["CONTROLS"][1] < 4):
				match(entry["CONTROLS"][0]):
					case 0:
						entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
						entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
					case 1:
						entry["STRINGS"] = [readString(file)]
						entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
					case 2:
						entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
						entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
						entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					case 3:
						pass
					case 4:
						entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
					case 5:
						entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
						entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
					case 6:
						entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
					case 7:
						entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
					case _:
						print("UNKNOWN 0x6A CONTROL: 0x%x" % entry["CONTROLS"][0])
						print("OFFSET: 0x%x" % (file.tell() - 3))
						sys.exit()
		
		case 0x6B:
			entry["TYPE"] = "0x6B"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["STRINGS"] = [readString(file), readString(file)]
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
		
		case 0x6C:
			entry["TYPE"] = "0x6C"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
		
		case 0x6D:
			entry["TYPE"] = "0x6D"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
			entry["STRINGS"] = [readString(file)]
		
		case 0x6E:
			entry["TYPE"] = "0x6E"
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little")
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			if (entry["CONTROL"] == 5):
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
		
		case 0x6F:
			entry["TYPE"] = "0x6F"
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little")
			if (entry["CONTROL"] == 0):
				entry["STRINGS"] = [readString(file)]
			elif (entry["CONTROL"] in [1, 2]):
				entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
				entry["STRINGS"] = [readString(file)]
			else:
				print("UNKNOWN 0x6F CONTROL: 0x%x" % entry["CONTROL"])
				print("OFFSET: 0x%x" % (file.tell() - 2))
				sys.exit()

		case 0x70:
			entry["TYPE"] = "0x70"
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little")
			if (entry["CONTROL"] == 1):
				entry["STRINGS"] = [readString(file)]
				entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
				entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
		
		case 0x71:
			entry["TYPE"] = "0x71"
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little")
			if (entry["CONTROL"] == 0):
				entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
		
		case 0x72:
			entry["TYPE"] = "0x72"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
		
		case 0x73:
			entry["TYPE"] = "0x73"
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little")
			check = [0, 1]
			if (entry["CONTROL"] in check):
				return
			match(entry["CONTROL"]):
				case 3:
					entry["UNK"] = [int.from_bytes(file.read(4), byteorder="little", signed=True)]
					entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
					entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
				case 5:
					entry["UNK"] = [struct.unpack("<f", file.read(4))[0]]
				case _:
					if (entry["CONTROL"] in [6, 2, 4]):
						entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
					else:
						print("UNKNOWN 0x73 CONTROL: 0x%x" % entry["CONTROL"])
						print("OFFSET: 0x%x" % (file.tell() - 2))
						sys.exit()

		case 0x74:
			entry["TYPE"] = "0x74"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
		
		case 0x77:
			entry["TYPE"] = "0x77"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
		
		case 0x78:
			entry["TYPE"] = "0x78"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))

		case 0x79:
			entry["TYPE"] = "0x79"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
		
		case 0x7B:
			entry["TYPE"] = "0x7B"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["STRINGS"] = [readString(file)]
		
		case 0x7D:
			entry["TYPE"] = "0x7D"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
		
		case 0x7E:
			entry["TYPE"] = "0x7E"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
		
		case 0x7F:
			entry["TYPE"] = "0x7F"
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little", signed=True)
			if (entry["CONTROL"] in [-1, -2]):
				entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
				entry["STRINGS"] = [readString(file)]
				entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
			elif (entry["CONTROL"] in [0, 1]):
				entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				entry["STRINGS"] = [readString(file), readString(file)]
			else:
				entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
				entry["STRINGS"] = [readString(file)]
				entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
		
		case 0x81:
			entry["TYPE"] = "0x81"
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little", signed=True)
			if (entry["CONTROL"] in [0, 3, 4]):
				entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
		
		case 0x82:
			entry["TYPE"] = "0x82"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
		
		case 0x83:
			entry["TYPE"] = "0x83"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
		
		case 0x84:
			entry["TYPE"] = "0x84"
		
		case 0x85:
			entry["TYPE"] = "0x85"
			entry["STRINGS"] = [readString(file)]
			entry["UNK"] = [int.from_bytes(file.read(4), byteorder="little", signed=True)]
		
		case 0x86:
			entry["TYPE"] = "0x86"
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little", signed=True)
			if (entry["CONTROL"] in [0, 1]):
				entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
		
		case 0x87:
			entry["TYPE"] = "0x87"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
		
		case 0x88:
			entry["TYPE"] = "0x88"
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little", signed=True)
			if (entry["CONTROL"] == 0):
				entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
		
		case 0x89:
			entry["TYPE"] = "0x89"
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little", signed=True)
			if (entry["CONTROL"] == 0):
				entry["UNK"] = [int.from_bytes(file.read(4), byteorder="little", signed=True)]
		
		case 0x8A:
			entry["TYPE"] = "0x8A"
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little", signed=True)
			if (entry["CONTROL"] == 0):
				entry["STRINGS"] = [readString(file), readString(file)]
		
		case 0x8C:
			entry["TYPE"] = "0x8C"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
		
		case 0x8D:
			entry["TYPE"] = "0x8D"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
		
		case 0x8E:
			entry["TYPE"] = "0x8E"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
		
		case 0x90:
			entry["TYPE"] = "0x90"
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little", signed=True)
			if (entry["CONTROL"] == 0):
				entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
		
		case 0x91:
			entry["TYPE"] = "0x91"
			entry["CONTROL"] = int.from_bytes(file.read(1), byteorder="little", signed=True)
			if (entry["CONTROL"] == 0):
				entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
				entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			
		case 0x92:
			entry["TYPE"] = "0x92"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
		
		case 0x93:
			entry["TYPE"] = "0x93"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
		
		case 0x94:
			entry["TYPE"] = "0x94"
			entry["UNK"] = [int.from_bytes(file.read(4), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			
		case 0x95:
			entry["TYPE"] = "0x95"

		case 0x96:
			entry["TYPE"] = "0x96"
			entry["UNK"] = [int.from_bytes(file.read(4), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
		
		case 0x97:
			entry["TYPE"] = "0x97"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
		
		case 0x98:
			entry["TYPE"] = "0x98"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
		
		case 0x99:
			entry["TYPE"] = "0x99"
		
		case 0x9E:
			entry["TYPE"] = "0x9E"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
		
		case 0x9F:
			entry["TYPE"] = "0x9F"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
			entry["STRINGS"] = [readString(file), readString(file)]
		
		case 0xA1:
			entry["TYPE"] = "0xA1"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
		
		case 0xA2:
			entry["TYPE"] = "0xA2"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]

		case 0xA3:
			entry["TYPE"] = "0xA3"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
			entry["UNK"].append(struct.unpack("<f", file.read(4))[0])
		
		case 0xA5:
			entry["TYPE"] = "0xA5"
			entry["UNK"] = [int.from_bytes(file.read(2), byteorder="little", signed=True)]
		
		case 0xA6:
			entry["TYPE"] = "0xA5"
			entry["UNK"] = [int.from_bytes(file.read(1), byteorder="little", signed=True)]
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
			entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))

		case _:
			print("UNKNOWN COMMAND: 0x%x" % cmd)
			print("Offset: 0x%x" % (file.tell() - 1))
			sys.exit()
		
	return entry

def GenerateMonsters(file, until_offset = None):
	print("READING MONSTERS")
	print("OFFSET: 0x%x" % file.tell())
	entry = {}
	entry["UNK"] = []
	entry["TYPE"] = "CREATE_MONSTERS"
	firstByte = file.read(1)
	file.seek(-1, 1)
	if (firstByte == b"\xFF"):
		entry["UNK"].append(file.read(0x1C).hex().upper())
		return entry
	entry["MAP"] = readString(file)
	file.seek(0x10 - (len(entry["MAP"]) + 1), 1)
	entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
	entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
	entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
	entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
	entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
	entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
	entry["UNK"].append(int.from_bytes(file.read(2), byteorder="little", signed=True))
	while(True):
		entry["UNK"].append(int.from_bytes(file.read(4), byteorder="little", signed=True))
		entry["STRINGS"] = []
		for i in range(0, 8):
			string = readString(file)
			entry["STRINGS"].append(string)
			file.seek(0x10 - (len(string) + 1), 1)
		for i in range(0, 8):
			entry["UNK"].append(int.from_bytes(file.read(1), byteorder="little", signed=True))
		check = int.from_bytes(file.read(4), byteorder="little", signed=True)
		file.seek(-4, 1)
		if (check == 0):
			entry["UNK"].append(file.read(8).hex().upper())
		else:
			string = readString(file)
			entry["STRINGS"].append(string)
			file.seek(12 - (len(string) + 1), 1)

		check = file.read(1)
		file.seek(-1, 1)
		if (check == b"\xFF"): break
		if (file.tell() == (until_offset - 4)): break
	
	if (file.tell() == (until_offset - 4)):
		check = int.from_bytes(file.read(4), byteorder="little")
		if (check != 1):
			print("UNEXPECTED MONSTERS ENDING: 0x%x" % check)
			print("OFFSET: 0x%x" % (file.tell() - 4))
			sys.exit()
	else:
		entry["UNK"].append(file.read(0x1C).hex().upper())
	return entry


files = glob.glob("nx/*.dat")
os.makedirs("jsons", exist_ok=True)

for y in range(0, len(files)):
	print(files[y])
	file = open(files[y], "rb")

	DUMP = {}

	file_size = GetFileSize(file)
	header_size = int.from_bytes(file.read(4), byteorder="little")
	string_id_offset = int.from_bytes(file.read(4), byteorder="little")
	functions_pointer_table_offset = int.from_bytes(file.read(4), byteorder="little")
	size_of_functions_pointer_table = int.from_bytes(file.read(4), byteorder="little")
	function_names_pointer_table_offset = int.from_bytes(file.read(4), byteorder="little")
	function_names_count = int.from_bytes(file.read(4), byteorder="little")
	end_of_function_names_table = int.from_bytes(file.read(4), byteorder="little")

	DUMP["HEADER"] = {}
	DUMP["HEADER"]["TYPE"] = "%X" % int.from_bytes(file.read(4), byteorder="little")
	DUMP["HEADER"]["ID"] = readString(file)

	FUNCTIONS_POINTERS = []
	FUNCTIONS_NAMES = []

	pos = file.tell()

	assert(pos == functions_pointer_table_offset)

	while(file.tell() < pos + size_of_functions_pointer_table):
		FUNCTIONS_POINTERS.append(int.from_bytes(file.read(4), byteorder="little"))

	pos = file.tell()

	assert(pos == function_names_pointer_table_offset)

	for i in range(0, function_names_count):
		ptr = int.from_bytes(file.read(2), byteorder="little")
		cur_pos = file.tell()
		file.seek(ptr)
		FUNCTIONS_NAMES.append(readString(file))
		file.seek(cur_pos)

	DUMP["FUNCTIONS"] = {}

	for i in range(0, function_names_count):
		DUMP["FUNCTIONS"]["%s" % FUNCTIONS_NAMES[i] if (FUNCTIONS_NAMES[i] != "") else "%04d" % i] = []
		file.seek(FUNCTIONS_POINTERS[i])
		if (i < (function_names_count - 1)):
			end = FUNCTIONS_POINTERS[i + 1]
		else:
			end = file_size
		while(file.tell() < end):
			if (FUNCTIONS_NAMES[i] != ""):
				cmd = int.from_bytes(file.read(1), byteorder="little")
				DUMP["FUNCTIONS"]["%s" % FUNCTIONS_NAMES[i]].append(GenerateCommand(cmd, file, end))
			else:
				tell_pos = file.tell()
				try:
					string = readString(file)
				except:
					file.seek(tell_pos)
					cmd = int.from_bytes(file.read(1), byteorder="little")
					DUMP["FUNCTIONS"]["%04d" % i].append(GenerateCommand(cmd, file, end))
				else:
					file.seek(tell_pos)
					if ((len(string) == 6) and (ord(string[0]) >= 0x20)):
						DUMP["FUNCTIONS"]["%04d" % i].append(GenerateMonsters(file, end))
					else:
						cmd = int.from_bytes(file.read(1), byteorder="little")
						DUMP["FUNCTIONS"]["%04d" % i].append(GenerateCommand(cmd, file, end))

	file.close()

	file = open("jsons/%s.json" % files[y][3:-4], "w", encoding="UTF-8")
	json.dump(DUMP, file, indent="\t", ensure_ascii=False)
	file.close()