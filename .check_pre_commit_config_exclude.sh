#!/bin/bash -e

# Return the module list excluded into `pre-commit-config.yaml`
# List is formated like this: odoo/local-src/module/|odoo/local-src/modeule2/
before=$(head -1 .pre-commit-config.yaml | grep exclude | sed "s/exclude: //g" | xargs)

# Return the specific module list uninstallable
current=$(for i in $(find . -name "__manifest__.py" -print); do egrep -l "installable.+False" $i; done | sort | xargs | sed 's/__manifest__.py /|/g' | sed 's/__manifest__.py//g' | grep . | xargs)

# If 2 lists are different, we need to launch `project.sync` invoke command to regenerate `pre-commit-config.yaml`
if [ "$before" != "$current" ];
    then
        echo 'Module list excluded into "pre-commit-config.yaml" is not updated.'
        echo 'Please launch `project.sync` invoke command to automatically update list.'
        echo 'Or edit "pre-commit-config.yaml" file to update list manually.'
        echo 'First line of "pre-commit-config.yaml" file must be: '
        echo 'exclude: '$current
        exit 1
fi
