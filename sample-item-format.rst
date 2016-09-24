(Data repeated for each sample 1-15 or 1-31)
22        Sample's name, padded with null bytes. If a name begins with a
          '#', it is assumed not to be an instrument name, and is
          probably a message.
2         Sample length in words (1 word = 2 bytes). The first word of
          the sample is overwritten by the tracker, so a length of 1
          still means an empty sample. See below for sample format.
1         Lowest four bits represent a signed nibble (-8..7) which is
          the finetune value for the sample. Each finetune step changes
          the note 1/8th of a semitone. Implemented by switching to a
          different table of period-values for each finetune value.
1         Volume of sample. Legal values are 0..64. Volume is the linear
          difference between sound intensities. 64 is full volume, and
          the change in decibels can be calculated with 20*log10(Vol/64)
2         Start of sample repeat offset in words. Once the sample has
          been played all of the way through, it will loop if the repeat
          length is greater than one. It repeats by jumping to this
          position in the sample and playing for the repeat length, then
          jumping back to this position, and playing for the repeat
          length, etc.
2         Length of sample repeat in words. Only loop if greater than 1.




					   22 char   Sample name, padded with zeroes to
								 full length.
						2 word   Sample length / 2. Needs to be multiplied
								 by 2 to get the actual length. If the sample
								 length is greater than 8000h, the sample
								 is bigger than 64k.
						1 byte   Sample finetune. Only the lower nibble is
								 valid. Fine tune table :
								  0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
								  0 +1 +2 +3 +4 +5 +6 +7 -8 -7 -6 -5 -4 -3 -2 -1
						1 byte   Sample volume (0-40h)
						1 word   Sample loop start / 2
						1 word   Sample loop length / 2
