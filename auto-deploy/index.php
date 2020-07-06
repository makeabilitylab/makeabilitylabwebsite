<?php
// This is a simple web service to support auto-deploy with gitlab.
// The idea is that you set up a deploy key on your repo using our public key,
// and a push hook pointing here.  Now when you push to the repo, it should
// trigger a pull into your deployment directory.
// This could be extended to support builds, tests, logging, etc.

require_once('config.php');
_trace("Auto-deploy: loaded config\n");

// Parse the headers
$headers = getallheaders();
_trace(json_encode($headers, JSON_PRETTY_PRINT) . "\n");

// Parse the body of the request
$jsonBody = file_get_contents('php://input');
$req = json_decode($jsonBody, true);
$r = print_r($req, true);
_trace($r. "\n");


// Allowed HTTP methods defined in config
if (!in_array($_SERVER['REQUEST_METHOD'], $ALLOWED_HTTP_METHODS)) {
    _log("Unsupported method: " . $_SERVER['REQUEST_METHOD'] . "\n");
    exit;
}

$gitSystem=null;
if(isset($headers['X-Gitlab-Event'])){
	$gitSystem="Gitlab";
	$urlvar='url';

}
if(isset($headers['X-GitHub-Event'])){
	$gitSystem="GitHub";
	$urlvar='ssh_url';
}

if($gitSystem){
	$header="X-".$gitSystem."-Event";
}

//Detarmine if we're on Test or Prod and set a flag
if ($_SERVER['HTTP_HOST'] == $TEST_HOSTNAME){
	$HOSTNAME=$TEST_HOSTNAME;
	$OPERATION=$TEST_MODE;
}
if ($_SERVER['HTTP_HOST'] == $PROD_HOSTNAME){
	$HOSTNAME=$PROD_HOSTNAME;
	$OPERATION=$PROD_MODE;
}



//Require Gitlab hook type in the header.
if (!$gitSystem) {
    _log("Expected header 'X-Git[lab|hub]-Event' not found! \n");
    exit;
} else if (!in_array($headers[$header], $DEPLOY_TRIGGERS)) {
    _log("Ignoring event: " . $headers[$header] . "; auto-deploy configured to deploy on : " .
         json_encode($DEPLOY_TRIGGERS, JSON_PRETTY_PRINT) . " \n");
    exit;
}

//Make a determiniation if the incoming operation is right for this system.
if($gitSystem && $HOSTNAME && $OPERATION){
	$refs=explode("/",$req['ref']);
	$incomingOp=$refs[1]; // should be tags or heads
	
	//Some initial validation, make sure this is a configured repo and stuff
	if(isset($req['repository']['url'])){
		
		$url = validateURL($req['repository'][$urlvar],$DEFINED_REPOS);;
	
		if(!$url){
			_log("This repository is not configured for autodeploy on this system");
			exit;
		}
		else{
			$deploy_to=$DEFINED_REPOS[$url]['deploy_to'];
		}
	}
	else{
		_log("No request json appears to have been sent");
		exit;
	}
	
	//Make sure we're doing a TAG or BRANCH as appropriate
	if(($incomingOp == "tags" && $OPERATION = "TAG") || ($incomingOp == "heads" && $refs[2] == $OPERATION)){
		//possibly need to clone it or pull it first:
		
	        $out = do_clone_or_pull(DEPLOY_KEY,$url,$deploy_to, $OPERATION);
	        _debug("$out\n");
		
	        //The following will ensure we're either on the right branch, or the right tag:
	        $out = do_checkout_branch($req,$deploy_to, $OPERATION);
	        _debug("$out\n");
	
		//If we're using docker, then do someother stuff
                if($USE_DOCKER){

                        _log("Deploying Containers...\n");
                        foreach($DEFINED_REPOS[$url]['containers'] as $container){

                                _log("Deploying $container\n");
                                deploy_container($BASE_DIR, $container);
                        }

                        _log("Container Build Backgrounded...\n");
                }

	}
	else{
		//There be dragons here
		_log("The incoming refs do not appear to be approprate to the mode chosen for this system (TAG/branch name)");
		exit;
	}
	

_log("Autodeploy complete");
}

/*
* Validates an incoming repo url against configured repos
*/
function validateURL($incoming, $configArray){
	$result = null;

	if(array_key_exists($incoming, $configArray)){
		$result = $incoming;
	}

	return $result;
}

/**
 * 
 * Will deploy or redeploy a container
 * @param string $deployto
 * @param string $containername
 */
function deploy_container($deployto,$containername){
	$cmd="nohup /usr/bin/php deploy.php $deployto $containername >/dev/null 2>&1 &";
	_log("Calling: $cmd\n");
	exec($cmd);
	return;
}

/**
 * Will checkout a Tag ona Tag Push Hook
 *
 * @param string $ref
 * @param string $deployto
 */
function do_checkout_branch($req, $deployto, $operation){
        
	if($operation != "TAG"){
	//if($operation == "Push Hook" && !empty($DEPLOY_BRANCH)){
		$branch=determine_branch_name($req);
		if($branch == $operation){
			$cmd = "bash -c 'cd $deployto; git checkout $branch' 2>&1";
		}
		else{
			$cmd = "bash -c 'cd $deployto; git checkout $operation' 2>&1";
		}
	}
	else{
		$tag= $req['ref'];
		$cmd = "bash -c 'cd $deployto; git checkout $tag' 2>&1";
	}
	
	if(file_exists($deployto . "/.gitmodules")){
		_log("Initializing and Updating submodules...\n");
		$subcmd = "bash -c 'cd $deployto; git submodule init; git submodule update' 2>&1";
	}

	_debug("Operation: $operation\n");
        _log("Exec Command: $cmd\n");

	$result = shell_exec($cmd);
	if(isset($subcmd)){
		$result .= shell_exec($subcmd);
 	}
 	return $result;

}


/**
 * Determines whether the given event is happening to the given branch.
 * Only works (er, only tested) for push and merge events
 * 
 * @param string $desiredBranch
 * @param array $request
 */
function determine_branch_name( $request) {
    // push request, branch is in request[ref]
    if (isset($reqest['ref'])) {
        // strip out the refs/head nonsense -- doesn't look like bare
        // branch is listed anywhere in the request
        return preg_replace("|refs/heads/|", "", $request['ref']);
    }

    _log("Unable to determine branch name. Maybe this wasn't a pull or merge request?");
}

/**
 * If $path is a directory, try a pull, else try a clone.
 * 
 * @param string $key
 * @param string $url
 * @param string $path
 */
function do_clone_or_pull($key, $url, $path, $operation) {
    // Already a git repo there.  Do a pull.
    if ((is_dir($path)) && (file_exists($path . "/.git"))) {
	if($operation=="TAG"){
		return do_fetch($key,$url,$path);
	}
	else{
		return do_pull($key,$url,$path);
	}
    }
    
    // Try a clone
    $out = do_clone($key,$url,$path);
    if (!is_dir($path)) {
        $out .= "\nClone appeared to fail.\n";
    }
    return $out;
}




/**
 * Invoke ssh-agent to add the ssh key, then fetch.
 * 
 * @param string $key Path to SSH private key.
 * @param string $url Gitlab url to the repo.
 * @param string $path Deployment path.
 * @return string Command output
 */
function do_fetch($key,$url,$path) {
    $cmd = "ssh-agent bash -c 'cd $path; ssh-add $key; git fetch' 2>&1";
    _log("Exec command: $cmd\n");
    return shell_exec($cmd);
}

/**
 * Invoke ssh-agent to add the ssh key, then pull.
 * 
 * @param string $key Path to SSH private key.
 * @param string $url Gitlab url to the repo.
 * @param string $path Deployment path.
 * @return string Command output
 */
function do_pull($key,$url,$path) {
    $cmd = "ssh-agent bash -c 'cd $path; ssh-add $key; git reset --hard; git pull' 2>&1";
    _log("Exec command: $cmd\n");
    return shell_exec($cmd);
}

/**
 * Invoke ssh-agent to add the key, then clone.
 * 
 * @param string $key Path to SSH private key.
 * @param string $url Gitlab url to the repo.
 * @param string $path Deployment path.
 * @return string Command output
 */
function do_clone($key,$url,$path) {
    $cmd = "ssh-agent bash -c 'ssh-add $key; git clone $url $path' 2>&1";
    _log("Exec command: $cmd\n");
    return shell_exec($cmd);
}


/**
 * Log a message, only here to make some messages easy to turn off.
 */
function _trace($message) {
    if ($trace = TRUE) {
        _log($message);
    } 
}

/**
 * Log a message, only here to make some messages easy to turn off.
 */
function _debug($message) {
    if ($debug = TRUE) {
        _log($message);
    } 
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
