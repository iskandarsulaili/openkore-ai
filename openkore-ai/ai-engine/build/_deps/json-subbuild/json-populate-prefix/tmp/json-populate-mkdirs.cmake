# Distributed under the OSI-approved BSD 3-Clause License.  See accompanying
# file LICENSE.rst or https://cmake.org/licensing for details.

cmake_minimum_required(VERSION ${CMAKE_VERSION}) # this file comes with cmake

# If CMAKE_DISABLE_SOURCE_CHANGES is set to true and the source directory is an
# existing directory in our source tree, calling file(MAKE_DIRECTORY) on it
# would cause a fatal error, even though it would be a no-op.
if(NOT EXISTS "D:/RO/bot/renew/openkore-ai/ai-engine/build/_deps/json-src")
  file(MAKE_DIRECTORY "D:/RO/bot/renew/openkore-ai/ai-engine/build/_deps/json-src")
endif()
file(MAKE_DIRECTORY
  "D:/RO/bot/renew/openkore-ai/ai-engine/build/_deps/json-build"
  "D:/RO/bot/renew/openkore-ai/ai-engine/build/_deps/json-subbuild/json-populate-prefix"
  "D:/RO/bot/renew/openkore-ai/ai-engine/build/_deps/json-subbuild/json-populate-prefix/tmp"
  "D:/RO/bot/renew/openkore-ai/ai-engine/build/_deps/json-subbuild/json-populate-prefix/src/json-populate-stamp"
  "D:/RO/bot/renew/openkore-ai/ai-engine/build/_deps/json-subbuild/json-populate-prefix/src"
  "D:/RO/bot/renew/openkore-ai/ai-engine/build/_deps/json-subbuild/json-populate-prefix/src/json-populate-stamp"
)

set(configSubDirs Debug)
foreach(subDir IN LISTS configSubDirs)
    file(MAKE_DIRECTORY "D:/RO/bot/renew/openkore-ai/ai-engine/build/_deps/json-subbuild/json-populate-prefix/src/json-populate-stamp/${subDir}")
endforeach()
if(cfgdir)
  file(MAKE_DIRECTORY "D:/RO/bot/renew/openkore-ai/ai-engine/build/_deps/json-subbuild/json-populate-prefix/src/json-populate-stamp${cfgdir}") # cfgdir has leading slash
endif()
