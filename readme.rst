ModReader
=========

For a long time I've wanted to make transcriptions of music I created on the Amiga,
in the so-called SoundTracker Module format.

Of course there were utilities to convert them into other formats, and I have used
them e.g. to convert modules to midi files, but I still wanted to be able to make
stuff visible outside of the program needed to manipulate the music data.

So I built this "notation software for music trackers" -
to be able to view the notation in a
regular texteditor instead of a program specialized to view music notation.

In my implementation, drum instruments are shown together as indicators on which
timing event they are played, like this::

    h.h.h.h.h.h.h.h.
    ....s.......s...
    b.......b.......


whereas instrument tracks are shown as a compressed (in the sense that only
the notes played are shown) piano roll, like this::

    ... ... ... ... ... ... A 4 ... ... ... ... ... ... ... ... ...
    ... ... ... ... E 4 ... ... ... E 4 ... ... ... ... ... ... ...
    ... ... C#4 ... ... ... ... ... ... ... C#4 ... ... ... ... ...
    A 3 ... ... ... ... ... ... ... ... ... ... ... A 3 ... ... ...

It works in a few phases.

For starters, you have to select the module to transcribe and load it.

Next, you are presented with a list of the instrument samples used in the module.
You have to transfer the drum samples to a second list and assign a letter to each.
Because I sometimes use samples that contain more than one drum instrument,
I made it so that you can assign multiple letters to one instrument.
It's also possible to redefine the vertical order of the drum instruments either
by the sequence in which you transfer them or by reordering them in the list.

When all that is done you can press the button and a directory is created
at the chosen location (unless it already exists)
and files containing the transcripts are placed into it.
The location is predefined but can be changed either by supplying a different
default value in the config file, or by using the "Change" button and changing
the path in the file selector.
You get one file for the collected drums, a file for each remaining instrument
and a file containing some general data, such as the sequence of patterns.
I added a date/time stamp to the names so that the process can be repeated without
overwriting existing files.

Depending on the file extension, appropriate parsing and transcription routines
will be called.
In the parsing, the philosophy of the module format - defining repeatable blocks of
notes - is extended to the separation of instrument data. This should lead to files
that are easily comparable across the various possible formats they were transcribed
from..
At the moment the following file types are recognized:

- `.med`: OctaMed MMD0/MMD1 module format
- `.mod`: (Amiga) SoundTracker module format
- `.mid`: MIDI format
- `.mmp`: LMMS project format
- `.rpp`: Reaper project format (could be an older version)

The latter three file types have possibilities to include a separate drum track,
that is, one in which all the drum instruments have been put together.
If this is the case the parsing routine will recognize this so that the instruments
are presented in the right way.

Usage
-----

Enter ``python3 modreadergui.py`` on the command line. You may leave out the python3 part if you make the script executable.

Requirements
------------

- Python
- PyQt(5)
- If available, lxml is used for the xml parsing in mmpreader.
