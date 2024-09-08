#!/usr/bin/php -q
<?php
/**
 * Copyright (C) 2024 National Cyber and Information Security Agency of the Czech Republic
 * Simplified version cake.php that make possible to use snuffleupagus readonly_exec check
 * This can be removed after patched 2.4 version is releases
 */
const DS = DIRECTORY_SEPARATOR;
const CAKE_SHELL_DISPATCHER = 'Cake' . DS . 'Console' . DS . 'ShellDispatcher.php';

$appDir = dirname(__DIR__);
$composerInstall = $appDir . DS . 'Vendor' . DS . 'cakephp' . DS . 'cakephp' . DS . 'lib';

if (!include $composerInstall . DS . CAKE_SHELL_DISPATCHER) {
    trigger_error('Could not locate CakePHP core files.', E_USER_ERROR);
}
unset($composerInstall);

return ShellDispatcher::run($argv);