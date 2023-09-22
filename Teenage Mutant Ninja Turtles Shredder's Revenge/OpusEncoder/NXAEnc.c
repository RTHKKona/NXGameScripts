/*Work based on code from here:
https://gist.github.com/tellowkrinkle/91423d561d8976be418ba770b9499bb3

PCM raw audio file was converted correctly only if file was:
- 48000 Hz
- S16LE
*/

#include <stdint.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <getopt.h>
#include <opus.h>

typedef struct uint32_be {
	uint8_t data[4];
} uint32_be_t;

struct NXAHeader {
	uint32_t MAGIC;
	uint32_t chunksize;
	uint8_t version;
	uint8_t channelCount;
	uint16_t dunno; //frameSize?
	uint32_t sampleRate;
	uint16_t dataOffset;
	uint32_t unknown[2];
	uint32_t preSkip;
	uint32_t MAGIC2;
	uint32_t streamSize;
};

uint32_be_t make_32_be(uint32_t i) {
	uint32_be_t o;
	o.data[0] = (i >> 24) & 0xFF;
	o.data[1] = (i >> 16) & 0xFF;
	o.data[2] = (i >>  8) & 0xFF;
	o.data[3] = (i >>  0) & 0xFF;
	return o;
}

struct NXAv1FrameHeader {
	uint32_be_t dataSize;
	uint32_t hash;
};

struct OutputBuffer {
	struct OutputBuffer *next;
	uint8_t data[];
};

uint32_t fakeCRC(uint8_t* buffer, size_t size) {
	uint32_t crc = 0;
	for (size_t i = 0; i < size; i++) {
		crc ^= buffer[i] << 24;
		for (size_t x = 0; x < 8; x++) {
			if (crc & 0x80000000)
				crc = (crc << 1) ^ 0x104c11db7;
			else crc = crc << 1;
		}
	}
	return crc;
}

void printUsage(const char *progName) {
	fprintf(stderr, "Usage: %s OPTIONS\n", progName);
	const char *str =
	"Options:\n"
	"\t-r sampleRate:  Sample rate (default: 48000)\n"
	"\t-c channels:    Number of channels (default: 2)\n"
	"\t-s frameSize:   Size of a frame in samples (default: 960)\n"
	"\t-f frameBytes:  Size of an encoded frame in bytes (default: 480)\n"
	"\t-v voiceMode:   Set encoder into speech-optimized mode (default: 0)\n"
	"\t-i inputFile:   Path to input file of raw s16le audio (default: stdin)\n"
	"\t-o outputFile:  Path to output opus file (default: stdout)\n";
	fputs(str, stderr);
	exit(EXIT_FAILURE);
}

int main(int argc, char *argv[]) {
	int sampleRate = 48000;
	int channels = 2;
	int frameSize = 960;
	int frameBytes = 480;
	int version = 0;
	int repeatStartSamples = 0;
	int repeatEndSamples = 0;
	int voiceMode = 0;
	FILE *input = stdin;
	FILE *output = stdout;

	int option;
	while ((option = getopt(argc, argv, "r:c:s:f:i:o:v:")) != -1) {
		switch (option) {
			case 'r': sampleRate = atoi(optarg); break;
			case 'c': {
				channels   = atoi(optarg);
				if ((channels < 1) || (channels > 2)) {
					fprintf(stderr, "Option -c requires an argument 1 or 2!\n");
					printUsage(argv[0]);
				}
				 break;
			}
			case 'v': {
				voiceMode = atoi(optarg); 
				if ((voiceMode < 0) || (voiceMode > 1)) {
					fprintf(stderr, "Option -v requires an argument 0 or 1!\n");
					printUsage(argv[0]);
				}
				break;
			}
			case 's': frameSize  = atoi(optarg); break;
			case 'f': frameBytes = atoi(optarg); break;
			case 'i':
				input = fopen(optarg, "rb");
				break;
			case 'o':
				output = fopen(optarg, "wb+");
				break;
			case '?':
				if (strchr("rcsfiov", optopt)) {
					fprintf(stderr, "Option %c requires an argument\n", optopt);
					printUsage(argv[0]);
				}
				fprintf(stderr, "Unknown option %c\n", optopt);
				printUsage(argv[0]);
		}
	}

	if (!input || !output) {
		fprintf(stderr, "Couldn't open %s file!\n", input ? "output" : "input");
		printUsage(argv[0]);
	}

	if (isatty(fileno(input)) || isatty(fileno(output))) {
		printUsage(argv[0]);
	}

	int sampleSize = channels * sizeof(short);
	float framesPerSecond = (float)sampleRate / (float)frameSize;
	float bitsPerSecond = framesPerSecond * frameBytes * 8;
	int frameHeaderBytes = version == 0 ? 8 : 0;

	int err;
	OpusEncoder *enc;
	if (voiceMode) enc = opus_encoder_create(sampleRate, channels, OPUS_APPLICATION_RESTRICTED_LOWDELAY, &err);
	else enc = opus_encoder_create(sampleRate, channels, OPUS_APPLICATION_AUDIO, &err);
	opus_encoder_ctl(enc, OPUS_SET_VBR(0));
	opus_encoder_ctl(enc, OPUS_SET_BITRATE((int)bitsPerSecond));

	void *inputBuffer = malloc(frameSize * sampleSize);
	struct OutputBuffer *head = NULL, *tail = NULL;
	int frames = 0;
	int numSamples = 0;

	while (1) {
		memset(inputBuffer, 0, frameSize * sampleSize);
		unsigned long amt = fread(inputBuffer, sampleSize, frameSize, input);
		if (amt == 0) { break; }
		frames++;
		numSamples += amt;

		struct OutputBuffer *tmp = malloc(sizeof(struct OutputBuffer) + frameBytes);
		tmp->next = NULL;
		if (!head) { head = tmp; }
		if (tail) { tail->next = tmp; }
		tail = tmp;

		int err = opus_encode(enc, inputBuffer, frameSize, tmp->data, frameBytes);
		if (err != frameBytes) {
			fprintf(stderr, "Encoder failed: %d\n", err);
			return EXIT_FAILURE;
		}
	}

	struct NXAHeader header = {
		.MAGIC = 0x80000001,
		.MAGIC2 = 0x80000004,
		.chunksize = 24,
		.version = version,
		.dataOffset = 0x20,
		.streamSize = 0,
		.sampleRate = sampleRate,
		.channelCount = channels,
		.dunno = 0x0,
		.unknown = {0},
		.preSkip = 0x78
	};

	fwrite(&header, sizeof(header), 1, output);
	size_t offset = ftell(output);
	for (struct OutputBuffer *frame = head; frame; frame = frame->next) {
		struct NXAv1FrameHeader frameHeader = {
			.hash = fakeCRC(frame->data, frameBytes),
			.dataSize = make_32_be(frameBytes)
		};
		fwrite(&frameHeader, sizeof(frameHeader), 1, output);
		fwrite(frame->data, frameBytes, 1, output);
	}
	size_t final_size = ftell(output);
	size_t stream_size = final_size - offset;
	fseek(output, 0x24, 0);
	fwrite(&stream_size, sizeof(uint32_t), 1, output);
	fseek(output, 0, 0);
	void* temp_whole_buffer = malloc(final_size);
	fread(temp_whole_buffer, final_size, 1, output);
	fclose(output);

	printf("Finished. Bitrate: %0.f kbps\n", bitsPerSecond/1000);

	return 0;
}
