export interface RequestReceived {
  request: {
    uuid: string;
    type: string;
    token_id: string;
    team_id: number;
    ip: string;
    hostname: string;
    method: string;
    user_agent: string;
    content: string; // <-- sended content here!
    query: any; // could be null
    headers: {
      [key: string]: string[];
    };
    url: string;
    size: number;
    files: any[];
    created_at: string;
    updated_at: string;
    sorting: number;
    custom_action_output: any[];
    custom_action_errors: any[];
    time: number;
  };
  total: boolean;
  truncated: boolean;
  runtime_variables: {
    [key: string]: string | number | null;
  };
}
