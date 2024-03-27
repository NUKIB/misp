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

            $remoteIp = function() {
                $clientIpHeader = Configure::read('MISP.log_client_ip_header');
                if ($clientIpHeader && isset($_SERVER[$clientIpHeader])) {
                    $headerValue = $_SERVER[$clientIpHeader];
                    // X-Forwarded-For can contain multiple IPs, see https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Forwarded-For
                    if (($commaPos = strpos($headerValue, ',')) !== false) {
                        $headerValue = substr($headerValue, 0, $commaPos);
                    }
                    $remoteIp = trim($headerValue);
                } else {
                    $remoteIp = $_SERVER['REMOTE_ADDR'] ?? null;
                }

                return $remoteIp;
            };

            App::uses('AuthComponent', 'Controller/Component');
            $authUser = AuthComponent::user();
            if (!empty($authUser)) {
                $user = [
                    'id' => $authUser['id'],
                    'email' => $authUser['email'],
                    'ip_address' => $remoteIp(),
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

    App::uses('CakeLogInterface', 'Log');
    class SentryLog implements CakeLogInterface
    {
        const LOG_LEVEL_BREADCRUMB = [
            'emergency' => Sentry\Breadcrumb::LEVEL_FATAL,
            'alert' => Sentry\Breadcrumb::LEVEL_FATAL,
            'critical' => Sentry\Breadcrumb::LEVEL_FATAL,
            'error' => Sentry\Breadcrumb::LEVEL_ERROR,
            'warning' => Sentry\Breadcrumb::LEVEL_WARNING,
            'notice' => Sentry\Breadcrumb::LEVEL_WARNING,
            'info' => Sentry\Breadcrumb::LEVEL_INFO,
            'debug' => Sentry\Breadcrumb::LEVEL_DEBUG,
        ];

        public function write($type, $message)
        {
            Sentry\addBreadcrumb('log', $message, [], self::LOG_LEVEL_BREADCRUMB[$type]);
        }
    }

    CakeLog::config('sentry', [
        'engine' => 'SentryLog',
        'types' => ['notice', 'info', 'debug', 'warning', 'error', 'critical', 'alert', 'emergency'],
    ]);
}

$sentryDsn = Configure::read('MISP.sentry_dsn');
if (!empty($sentryDsn)) {
    initializeSentry($sentryDsn);
}

// Send exceptions and PHP errors for SimpleBackgroundTask or when MIPS_AUTOMATIC_TASK environment variable is set to 'true'
// This overwrites default behaviour that just write logs to stderr
if (getenv('BACKGROUND_JOB_ID') || getenv('MISP_AUTOMATIC_TASK') === 'true') {
    $errorHandler = new ConsoleErrorHandler();

    Configure::write('Exception.consoleHandler', function (Throwable $exception) use ($errorHandler) {
        if (Configure::read('MISP.sentry_dsn')) {
            Sentry\captureException($exception);
        }
        if (Configure::read('Security.ecs_log')) {
            EcsLog::handleException($exception);
        }
        $errorHandler->handleException($exception);
    });
    Configure::write('Error.consoleHandler', function ($code, $description, $file = null, $line = null, $context = null) use ($errorHandler) {
        if (Configure::read('MISP.sentry_dsn')) {
            $exception = new \ErrorException($description, 0, $code, $file, $line);
            Sentry\captureException($exception);
        }
        if (Configure::read('Security.ecs_log')) {
            EcsLog::handleError($code, $description, $file, $line);
        }
        $errorHandler->handleError($code, $description, $file, $line);
    });
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

// Send error logs to syslog just when syslog is enabled in config
if (Configure::read('Security.syslog')) {
    CakeLog::config('syslog', array(
        'engine' => 'Syslog',
        'types' => array('warning', 'error', 'critical', 'alert', 'emergency'),
        'prefix' => 'MISP',
    ));
}

// Send error logs to socket in ECS JSON format just when ECS log is enabled in config
if (Configure::read('Security.ecs_log')) {
    CakePlugin::load('EcsLog');
    CakeLog::config('ecs', [
        'engine' => 'EcsLog.EcsLog',
        'types' => ['notice', 'info', 'debug', 'warning', 'error', 'critical', 'alert', 'emergency'],
    ]);
}

// Disable phar wrapper, because can be dangerous
if (in_array('phar', stream_get_wrappers(), true)) {
    stream_wrapper_unregister('phar');
}

