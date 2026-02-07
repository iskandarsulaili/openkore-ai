# GodTierAI Plugin Entry Point
# This file loads the GodTierAI module into OpenKore
# Without this .pl file, OpenKore cannot find and load the plugin

package godtier_ai;

use strict;
use warnings;
use FindBin qw($RealBin);
use lib "$RealBin/plugins";

# Load the main GodTierAI module
require "$RealBin/plugins/godtier-ai/GodTierAI.pm";

1;
