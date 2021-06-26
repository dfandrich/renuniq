---
title: renuniq
section: 1
header: User Manual
footer: renuniq ver. 1
date: June 24, 2021
---
# NAME
renuniq - Rename files following a user-defined template.

# SYNOPSIS
**renuniq** [**-?hmnwLV**] [**-c** countstart] [**-d** descriptor] [**-t** template] *filename ...*

# DESCRIPTION
**renuniq** is a program to rename batches of files in a user-specified
pattern. The pattern is specified in the form of a template can include a
sequentially-increasing number, the file extension, the unique ending of a
series of similarly-named files, the date or time of the file, and more. An
ideal application is renaming files from a digital camera to include meaningful
data.

The new file name is specified in the form of a template string. Within the
string, a number of substitutions are available which automatically adapt to
the given files. The following stay the same for all files:

**%{DESC}**
: user-specified descriptor

**%{UNIQSUFF}**
: the unique suffix in the list of all files

The following change for each file:

**%{DIR}**
: directory including trailing slash

**%{NAME}**
: file name

**%{NUM}**
: a 0-padded positive increasing integer of automatic width

**%{NUMn}**
:  0-padded positive increasing integer of width n (1<=n<=6)

**%{PATH}**
: full file name

**%{EXT}**
: file extension (section including the last .)

**%{NOTEXT}**
: file name up to the last .

Additionally, **strftime** parameters will be substituted in the same way as in
**strftime**. These will match the mtime of each file, unless the **-w** option
is given which selects the current time instead. The **-m** option turns off
**strftime** substitution altogether. For example '%Y%m' would be replaced by
the year and two-digit numeric month. To use a % character in a file name
literally, double it to '%%'.

# OPTIONS
**-c** *countstart*
: Start the sequential count at this integer. This is 1 by default.

**-d** *descriptor*
: Set the value of the substitution variable %{DESC}. This option is used to
create a default rename template with a placeholder than can easily be switched
from one run to another.

**-m**
: Turn off strftime variable substitution in template. Any % characters will
then be passed through unimpeded.

**-n**
: Print what would be executed but don't actually do it. The commands printed
are ready to be entered manually, if desired.

**-t** *template*
: Set the template of the renamed file name. Any special substitution variables
documented earlier will be replaced for each file.

**-w**
: Use the time now instead of mtime for strftime format strings.

**-L**
: Display the program license.

**-V**
: Display the program version.

# EXAMPLES
If there are three files in the current directory, **img_1111.jpg**,
**img_4444.jpg** and **img_7777.jpg**, images which were taken on 2021-04-01,
they can be renamed to **20210401_my_holiday_1.jpg**,
**20210401_my_holiday_2.jpg**, and **20210401_my_holiday_3.jpg** using the
command:

    renuniq -t '%Y%m%d_%{DESC}_%{NUM}%{EXT}' -d my_holiday img*

To rename the files **color-red**, **color-blue**, **color-green** to **colour-red**,
**colour-blue**, **colour-green**, use the command:

    renuniq -t 'colour-%{UNIQSUFF}' color-*

To rename all 100 files in a directory to **file001**, **file002**, and so on,
use the command:

    renuniq -t 'file%{NUM}' *

# EXIT STATUS
**renuniq** returns 0 on success or 1 on failure.

# FILES
**`$XDG_CONFIG_HOME/renuniqrc`**

**`$HOME/.renuniqrc`**

The default templates can be changed by adding options to one of these files.
The file consists primarily of lines matching:

    option="value"

where **option** can be one of the following:

**default_template**
: used when several files are being renamed and no descriptor is given

**default_template_single**
: used when a single file is being renamed and no descriptor is given

**default_template_desc**
: used when several files are being renamed and a descriptor is given

**default_template_desc_single**
: used when a single file is being renamed and a descriptor is given

The file is actually arbitrary Python, so comments, multi-line strings and
Python expressions can be used.

If **%{DESC}** is used in a complicated template, the **-d** option can then
easily insert a customized bit of text on each rename without having to specify
the entire template each time on the command-line.

# AUTHORS
Dan Fandrich <dan@coneharvesters.com>

# COPYRIGHT
Copyright 2006-2021 by Daniel Fandrich <dan@coneharvesters.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

# SEE ALSO
The **renuniq** project is at <https://github.com/dfandrich/renuniq>

**mmv**(1),
**mv**(1),
**strftime**(3)
