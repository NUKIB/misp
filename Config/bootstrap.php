<?php
if (isset($_SERVER['HTTP_X_FORWARDED_PROTO']) && strtolower($_SERVER['HTTP_X_FORWARDED_PROTO']) === 'https') {
    $_SERVER['HTTPS'] = "on"; // because we are behind reverse proxy that supports https

    $httpHost = env('HTTP_HOST');
    if (isset($httpHost)) {
        // `App.fullBaseUrl` is already defined, so we need to changed definition to generate proper redirect
        Configure::write('App.fullBaseUrl',  'https://' . $httpHost);
    }
    unset($httpHost);
}

// If X-Forwarded-For HTTP header is set, use it as remote address
if (isset($_SERVER['HTTP_X_FORWARDED_FOR'])) {
    $_SERVER['REMOTE_ADDR'] = explode(",", $_SERVER['HTTP_X_FORWARDED_FOR'])[0];
}

/**
 * This file is loaded automatically by the app/webroot/index.php file after core.php
 *
 * This file should load/create any application wide configuration settings, such as
 * Caching, Logging, loading additional configuration files.
 *
 * You should also use this file to include any files that provide global functions/constants
 * that your application uses.
 */

Cache::config('default', array('engine' => 'File'));
Configure::load('config');

function initializeSentry($sentryDsn) {
    $serverName = Configure::read('MISP.baseurl');
    $serverName = rtrim(str_replace('https://', '', $serverName), '/');

    $init = [
        'dsn' => $sentryDsn,
        'server_name' => $serverName,
        'send_default_pii' => true,
        'before_send' => function (\Sentry\Event $event): ?\Sentry\Event {
            if (defined('CAKEPHP_SHELL') && CAKEPHP_SHELL) { // do not start session for shell commands
                return $event;
            }

            App::uses('AuthComponent', 'Controller/Component');
            $authUser = AuthComponent::user();
            if (!empty($authUser)) {
                $user = [
                    'id' => $authUser['id'],
                    'email' => $authUser['email'],
                    'ip_address' => $_SERVER['REMOTE_ADDR'],
                    'logged_by_authkey' => isset($authUser['logged_by_authkey']),
                ];
                if (isset($authUser['authkey_id'])) {
                    $user['authkey_id'] = $authUser['authkey_id'];
                }
                $event->setUser(\Sentry\UserDataBag::createFromArray($user));
            }

            return $event;
        },
    ];
    $environment = Configure::read('MISP.sentry_environment');
    if ($environment) {
        $init['environment'] = $environment;
    }

    Sentry\init($init);
    Sentry\configureScope(function (Sentry\State\Scope $scope): void {
        $backgroundJobId = getenv('BACKGROUND_JOB_ID');
        if ($backgroundJobId) {
            $scope->setTag('job_id', $backgroundJobId);
        }
        if (isset($_SERVER['HTTP_X_REQUEST_ID'])) {
            $scope->setTag('request_id', $_SERVER['HTTP_X_REQUEST_ID']);
        }
    });
}

$sentryDsn = Configure::read('MISP.sentry_dsn');
if (!empty($sentryDsn)) {
    initializeSentry($sentryDsn);

    // SimpleBackgroundTask or when SENTRY_ENABLED is set to true
    if (getenv('BACKGROUND_JOB_ID') || getenv('SENTRY_ENABLED') === 'true') {
        $errorHandler = new ConsoleErrorHandler();

        Configure::write('Exception.consoleHandler', function (Throwable $exception) use ($errorHandler) {
            Sentry\captureException($exception);
            $errorHandler->handleException($exception);
        });
        Configure::write('Error.consoleHandler', function ($code, $description, $file = null, $line = null, $context = null) use ($errorHandler) {
            $exception = new \ErrorException($description, 0, $code, $file, $line);
            Sentry\captureException($exception);
            $errorHandler->handleError($code, $description, $file, $line, $context);
        });
    }
}

/**
 * Plugins need to be loaded manually, you can either load them one by one or all of them in a single call
 * Uncomment one of the lines below, as you need. make sure you read the documentation on CakePlugin to use more
 * advanced ways of loading plugins
 *
 * CakePlugin::loadAll(); // Loads all plugins at once
 * CakePlugin::load('DebugKit'); //Loads a single plugin named DebugKit
 *
 */

CakePlugin::load('SysLog');
CakePlugin::load('Assets'); // having Logable
CakePlugin::load('SysLogLogable');
CakePlugin::load('OidcAuth');

/**
 * Uncomment the following line to enable client SSL certificate authentication.
 * It's also necessary to configure the plugin — for more information, please read app/Plugin/CertAuth/reame.md
 */
// CakePlugin::load('CertAuth');
// CakePlugin::load('ShibbAuth');

/**
 * Configures default file logging options
 */
App::uses('CakeLog', 'Log');
CakeLog::config('debug', array(
	'engine' => 'FileLog',
	'types' => array('notice', 'info', 'debug'),
	'file' => 'debug',
));
CakeLog::config('error', array(
	'engine' => 'FileLog',
	'types' => array('warning', 'error', 'critical', 'alert', 'emergency'),
	'file' => 'error',
));
CakeLog::config('syslog', array(
    'engine' => 'Syslog',
    'types' => array('warning', 'error', 'critical', 'alert', 'emergency'),
    'prefix' => 'MISP',
));

// Disable phar wrapper, because can be dangerous
if (in_array('phar', stream_get_wrappers(), true)) {
    stream_wrapper_unregister('phar');
}

