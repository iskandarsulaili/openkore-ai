#!/usr/bin/perl
# Dependency checker for godtier_ai plugin
# This script verifies all required Perl modules are installed

use strict;
use warnings;

print "=" x 60 . "\n";
print "Checking godtier_ai Plugin Dependencies\n";
print "=" x 60 . "\n\n";

# Required modules for core functionality
my @required = qw(
    JSON
    Time::HiRes
);

# HTTP modules (at least one required)
my @http_modules = qw(
    LWP::UserAgent
    HTTP::Tiny
);

# Optional modules for enhanced functionality
my @optional = qw(
    Encode
    URI
);

my $all_ok = 1;
my $http_available = 0;

# Check required modules
print "Required Modules:\n";
print "-" x 60 . "\n";
foreach my $module (@required) {
    printf "  %-30s : ", $module;
    eval "require $module";
    if ($@) {
        print "✗ MISSING\n";
        print "    Error: $@\n";
        print "    Install: cpanm $module\n";
        $all_ok = 0;
    } else {
        my $version = eval "\$${module}::VERSION" || "unknown";
        print "✓ OK (version: $version)\n";
    }
}

# Check HTTP modules (at least one required)
print "\nHTTP Modules (at least one required):\n";
print "-" x 60 . "\n";
foreach my $module (@http_modules) {
    printf "  %-30s : ", $module;
    eval "require $module";
    if ($@) {
        print "✗ Not installed\n";
    } else {
        my $version = eval "\$${module}::VERSION" || "unknown";
        print "✓ Available (version: $version)\n";
        $http_available++;
    }
}

if ($http_available == 0) {
    print "\n";
    print "  ERROR: No HTTP library available!\n";
    print "  You need at least one of: LWP::UserAgent or HTTP::Tiny\n";
    print "  Install with: cpanm LWP::UserAgent\n";
    $all_ok = 0;
} else {
    print "\n  ✓ At least one HTTP library is available\n";
}

# Check optional modules
print "\nOptional Modules (recommended):\n";
print "-" x 60 . "\n";
foreach my $module (@optional) {
    printf "  %-30s : ", $module;
    eval "require $module";
    if ($@) {
        print "  Not installed (OK, but recommended)\n";
    } else {
        my $version = eval "\$${module}::VERSION" || "unknown";
        print "✓ Available (version: $version)\n";
    }
}

# Check Perl version
print "\nPerl Environment:\n";
print "-" x 60 . "\n";
printf "  Perl Version               : %s\n", $^V;
printf "  Perl Executable            : %s\n", $^X;
printf "  Operating System           : %s\n", $^O;

# Final summary
print "\n" . "=" x 60 . "\n";
if ($all_ok) {
    print "✓ SUCCESS: All required dependencies are installed!\n";
    print "✓ godtier_ai plugin should load successfully.\n";
    print "=" x 60 . "\n";
    exit 0;
} else {
    print "✗ FAILURE: Some required dependencies are MISSING!\n";
    print "✗ Plugin will NOT load until these are installed.\n";
    print "\n";
    print "Installation Instructions:\n";
    print "-" x 60 . "\n";
    print "1. Using CPAN Minus (recommended):\n";
    print "   cpanm LWP::UserAgent\n";
    print "   cpanm JSON\n";
    print "\n";
    print "2. Using system package manager:\n";
    print "   # Debian/Ubuntu:\n";
    print "   sudo apt-get install libwww-perl libjson-perl\n";
    print "\n";
    print "   # RedHat/CentOS:\n";
    print "   sudo yum install perl-libwww-perl perl-JSON\n";
    print "\n";
    print "   # Windows (Strawberry Perl):\n";
    print "   cpan LWP::UserAgent\n";
    print "   cpan JSON\n";
    print "\n";
    print "3. Manual download from CPAN:\n";
    print "   http://search.cpan.org/dist/libwww-perl/\n";
    print "   http://search.cpan.org/dist/JSON/\n";
    print "=" x 60 . "\n";
    exit 1;
}
