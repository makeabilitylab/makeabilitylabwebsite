using Microsoft.Office.Core;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using PowerPoint = Microsoft.Office.Interop.PowerPoint;

namespace PptToPdf
{
    // For saving to PDF using PowerPoint Interop, you must have PowerPoint installed
    // This program uses Office15
    class Program
    {
        class CommandLineArguments
        {
            public string InputDir = string.Empty;
            public string OutputDir = string.Empty;
            public bool OverwriteFiles = false;
        }

        private static readonly string COMMAND_HELP = "help";
        private static readonly string COMMAND_INPUT_DIR = "in_dir";
        private static readonly string COMMAND_OUTPUT_DIR = "out_dir";
        private static readonly string COMMAND_OVERWRITE_PDFS = "overwrite";

        private static Dictionary<string, string> MAP_COMMAND_TO_DESC = new Dictionary<string, string>()
        {
            {COMMAND_HELP, "displays this help menu"},
            {COMMAND_INPUT_DIR, "the input dir; if not specified, defaults to current"},
            {COMMAND_OUTPUT_DIR, string.Format("the output dir (must be full path); if not specified defaults to {0}", COMMAND_INPUT_DIR) },
            {COMMAND_OVERWRITE_PDFS, "overwrites pdfs with same path and filename (default: false)"},
        };

        static void Main(string[] args)
        {
            CommandLineArguments cmdLineArgs = ParseCommandLineArgs(args);

            // If the cmdLineArgs are null, print out help
            if (cmdLineArgs == null)
            {
                Console.WriteLine();
                PrintHelp();
                return;
            }

            // Create the output dir if it doesn't exist
            if (!Directory.Exists(cmdLineArgs.OutputDir))
            {
                Directory.CreateDirectory(cmdLineArgs.OutputDir);
            }

            Console.WriteLine("The input directory: {0}", cmdLineArgs.InputDir);
            Console.WriteLine("The output directory: {0}", cmdLineArgs.OutputDir);

            // Process and save PowerPoint thumbnails
            int pptIndex = 1;
            string[] pptFilesWithPath = Directory.GetFiles(cmdLineArgs.InputDir, "*.ppt*", SearchOption.AllDirectories);
            Console.WriteLine("Found {0} PowerPoint files", pptFilesWithPath.Length);
            var watch = System.Diagnostics.Stopwatch.StartNew();
            foreach (string pptFileNameWithPath in pptFilesWithPath)
            {
                string pptFileName = Path.GetFileName(pptFileNameWithPath);
                string pptPath = Path.GetDirectoryName(pptFileNameWithPath);
                string justFilenameNoExt = Path.GetFileNameWithoutExtension(pptFileNameWithPath);
                string pdfFilename = justFilenameNoExt + ".pdf";
                string pdfFilenameWithPath = Path.Combine(cmdLineArgs.OutputDir, pdfFilename);

                if (!cmdLineArgs.OverwriteFiles)
                {
                    pdfFilenameWithPath = GetUniqueFilename(pdfFilenameWithPath);
                }

                // The following PPT -> PDF conversion code is based on:
                // http://stackoverflow.com/questions/32582433/converting-powerpoint-presentations-ppt-x-to-pdf-without-interop
                
                // Create COM Objects
                PowerPoint.Application pptApplication = null;
                PowerPoint.Presentation pptPresentation = null;
                try
                {
                    object unknownType = Type.Missing;

                    //start power point
                    //TODO: for efficiency, could create this object once rather
                    //then everytime through the loop. Would have to change pptApplication.Quit() stuff
                    //below as well. This runs fine though, so not going to change it for now.
                    pptApplication = new PowerPoint.Application();

                    //open powerpoint document
                    pptPresentation = pptApplication.Presentations.Open(pptFileNameWithPath,
                        MsoTriState.msoTrue, MsoTriState.msoTrue, MsoTriState.msoFalse);

                    // save PowerPoint as PDF
                    pptPresentation.ExportAsFixedFormat(pdfFilenameWithPath,
                        PowerPoint.PpFixedFormatType.ppFixedFormatTypePDF,
                        PowerPoint.PpFixedFormatIntent.ppFixedFormatIntentPrint,
                        MsoTriState.msoFalse, PowerPoint.PpPrintHandoutOrder.ppPrintHandoutVerticalFirst,
                        PowerPoint.PpPrintOutputType.ppPrintOutputSlides, MsoTriState.msoFalse, null,
                        PowerPoint.PpPrintRangeType.ppPrintAll, string.Empty, true, true, true,
                        true, false, unknownType);
                }
                finally
                {
                    // Close and release the Document object.
                    if (pptPresentation != null)
                    {
                        pptPresentation.Close();
                        pptPresentation = null;
                    }

                    // Quit PowerPoint and release the ApplicationClass object.
                    if (pptApplication != null)
                    {
                        pptApplication.Quit();
                        pptApplication = null;
                    }
                }
            }

            watch.Stop();
            var elapsedMs = watch.ElapsedMilliseconds;
            Console.WriteLine("Processed {0} PowerPoint files in {1} ms", pptFilesWithPath.Length, elapsedMs);
            Console.WriteLine("Press any key to continue");
            Console.ReadLine();
        }

        private static void PrintHelp()
        {
            Console.WriteLine("Converts PowerPoint files (.pptx) to PDFs");

            foreach (KeyValuePair<string, string> kvp in MAP_COMMAND_TO_DESC)
            {
                Console.WriteLine("  -{0} : {1}", kvp.Key, kvp.Value);
            }

            Console.WriteLine();
            Console.WriteLine("Example usage:");
            Console.WriteLine("  Create pdfs of all pptx files in current directory");
            Console.WriteLine("\t>PptToPdf.exe");
            Console.WriteLine("  Create pdfs of all pptx files in c:\\mydocuments");
            Console.WriteLine("\t>PptToPdf.exe -in_dir \"c:\\mydocuments\"");
            Console.WriteLine("  Create pdfs of all pptx files in c:\\mydocuments and store in c:\\pdfs");
            Console.WriteLine("\t>PptToPdf.exe -in_dir \"c:\\mydocuments\" -out_dir \"c:\\pdfs\"");

            Console.WriteLine();
            Console.WriteLine("You must have MS Office 15 installed for PptToPdf to work.");
            Console.WriteLine();
            Console.WriteLine("Press any key to continue");
            Console.ReadLine();
        }

        static CommandLineArguments ParseCommandLineArgs(string[] args)
        {
            Dictionary<string, string> mapCmdLineArgs = new Dictionary<string, string>();
            for (int i = 0; i < args.Length; i += 2)
            {
                if (args[i].StartsWith("-") && (i + 1) < args.Length && !args[i + 1].StartsWith("-"))
                {
                    string key = args[i].Substring(1);

                    if (!MAP_COMMAND_TO_DESC.ContainsKey(key))
                    {
                        Console.WriteLine("The argument '{0}' is not a valid argument.", args[i]);
                        return null;
                    }

                    string value = args[i + 1];
                    mapCmdLineArgs[key] = value;
                }
                else if (args[i].Contains(COMMAND_HELP))
                {
                    return null;
                }
                else
                {
                    Console.WriteLine("The argument '{0}' could not be parsed. Each argument must have a value (e.g., -arg val)", args[i]);
                    return null;
                }
            }

            if (mapCmdLineArgs.ContainsKey(COMMAND_HELP))
            {
                return null;
            }

            CommandLineArguments cmdLineArgs = new CommandLineArguments();

            if (mapCmdLineArgs.ContainsKey(COMMAND_OVERWRITE_PDFS))
            {
                cmdLineArgs.OverwriteFiles = bool.Parse(mapCmdLineArgs[COMMAND_OVERWRITE_PDFS]);
            }


            if (mapCmdLineArgs.ContainsKey(COMMAND_INPUT_DIR))
            {
                cmdLineArgs.InputDir = mapCmdLineArgs[COMMAND_INPUT_DIR];
                cmdLineArgs.InputDir = Path.GetFullPath(cmdLineArgs.InputDir);
            }
            else
            {
                cmdLineArgs.InputDir = GetExecutingAssemblyPath();
            }

            if (mapCmdLineArgs.ContainsKey(COMMAND_OUTPUT_DIR))
            {
                cmdLineArgs.OutputDir = mapCmdLineArgs[COMMAND_OUTPUT_DIR];
                cmdLineArgs.OutputDir = Path.GetFullPath(cmdLineArgs.OutputDir);
            }
            else
            {
                cmdLineArgs.OutputDir = cmdLineArgs.InputDir;
            }

            return cmdLineArgs;
        }

        static string GetExecutingAssemblyPath()
        {
            string path = System.IO.Path.GetDirectoryName(System.Reflection.Assembly.GetExecutingAssembly().GetName().CodeBase);
            path = path.Replace("file:\\", "");
            return path;
        }

        static string GetUniqueFilename(string filename)
        {
            string originalFilename = filename;
            string justTheFilename = Path.GetFileNameWithoutExtension(filename);
            string originalPath = Path.GetDirectoryName(filename);
            int attempts = 1;
            while (File.Exists(filename))
            {
                string newfilename = string.Format("{0}({1})", justTheFilename, attempts++);
                filename = newfilename;
                if (Path.HasExtension(originalFilename))
                {
                    filename = newfilename + Path.GetExtension(originalFilename);
                }
                filename = Path.Combine(originalPath, filename);
            }
            return filename;
        }
    }
}
