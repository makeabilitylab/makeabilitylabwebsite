<?php
require_once('config.php');


/*
 * argv[1] is the path this is going to be deployed to
 * argv[2] is the container name
 */

if(isset($argv[1]) && isset($argv[2])){
	_log("Deploying $argv[2]\n");
	deploy_container($argv[1],$argv[2]);
}
else{
	_log("Something went wrong\n");
}

_log("Deploy script completed\n");

function deploy_container($deployto,$containername){
GLOBAL $MAIL_CONTAINER_BUILD_RESULTS;
GLOBAL $SEND_MAIL_TO;

$Logfile=LOG_FILE;

   $cmd = "bash -c 'cd $deployto/$containername; ./rebuildanddeploy.sh $containername 2>&1'";
    _log("Exec command: $cmd\n");
    $results = shell_exec($cmd);
    if($MAIL_CONTAINER_BUILD_RESULTS){
        send_mail($results);
    }
    _log($results);
    return;
}

/**
 * Will sent contain build results to a configured email address
 * 
 * @param string $messagebody
 */
function send_mail($messagebody){
GLOBAL $SEND_MAIL_TO;

    $subject = "Docker Autodeploy Build Results";
    $headers = "FROM: noreply@cs.washington.edu"."\r\n" .
            "REPLY-TO: noreply@cs.washington.edu"."\r\n";
    
    mail($SEND_MAIL_TO,$subject,$messagebody,$headers);
}

/**
 * Log a message to a file. Expected constant named LOG_FILE to be 
 * defined in config.php
 */
function _log($message) {
	file_put_contents(
        	LOG_FILE,
	        $message,
		FILE_APPEND
		);
	 }
