Each pattern has 64 rows.
Depending on the number of channels, each row has from 4 to 8 notes.
The channel count is determined by the ID. (see table 0005)
The number of patterns is the highest pattern number stored in the pattern list.

Each note has four bytes.
Four notes make up a track in a four channel MOD file.
Each track is saved sequentially :
  byte  0-3     4-7    8-11    12-15
      Chn #1  Chn #2  Chn #3  Chn #4
  byte 16-19   20-23  24-27    28-31
      Chn #1  Chn #2  Chn #3  Chn #4
1 word   Instrument / period
		 The instrument number is in bits 12-15, the 12-bit period in bits 0-11.
1 byte   Upper nibble : Lower 4 bits of the instrument,
		 Lower nibble : Special effect command.
1 byte   Special effects data
(Table 0005)
Protracker 16 note conversion table / MOD Period table
	   +-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+
PT16 : I    1I    2I    3I    4I    5I    6I    7I    8I    9I   10I   11I   12I
MOD  : I 1712I 1616I 1524I 1440I 1356I 1280I 1208I 1140I 1076I 1016I  960I  906I
Note : I  C-0I  C#0I  D-0I  D#0I  E-0I  F-0I  F#0I  G-0I  G#0I  A-0I  A#0I  B-0I
	   +-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+
	   I   13I   14I   15I   16I   17I   18I   19I   20I   21I   22I   23I   24I
	   I  856I  808I  762I  720I  678I  640I  604I  570I  538I  508I  480I  453I
	   I  C-1I  C#1I  D-1I  D#1I  E-1I  F-1I  F#1I  G-1I  G#1I  A-1I  A#1I  B-1I
	   +-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+
	   I   25I   26I   27I   28I   29I   30I   31I   32I   33I   34I   35I   36I
	   I  428I  404I  381I  360I  339I  320I  302I  285I  269I  254I  240I  226I
	   I  C-2I  C#2I  D-2I  D#2I  E-2I  F-2I  F#2I  G-2I  G#2I  A-2I  A#2I  B-2I
	   +-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+
	   I   37I   38I   39I   40I   41I   42I   43I   44I   45I   46I   47I   48I
	   I  214I  202I  190I  180I  170I  160I  151I  143I  135I  127I  120I  113I
	   I  C-3I  C#3I  D-3I  D#3I  E-3I  F-3I  F#3I  G-3I  G#3I  A-3I  A#3I  B-3I
	   +-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+
	   I   49I   50I   51I   52I   53I   54I   55I   56I   57I   58I   59I   60I
	   I  107I  101I   95I   90I   85I   80I   75I   71I   67I   63I   60I   56I
	   I  C-4I  C#4I  D-4I  D#4I  E-4I  F-4I  F#4I  G-4I  G#4I  A-4I  A#4I  B-4I
	   +-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+
